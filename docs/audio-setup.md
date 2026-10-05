# Audio setup

Everything needed to get the speakers and microphone working again on a fresh SD card.
Captured from the working system on 2026-10-04.

To rebuild, work through [Reinitializing on a new SD card](#reinitializing-on-a-new-sd-card) from top
to bottom. The rest of the file is reference.

## Hardware

- **Raspberry Pi 5 Model B Rev 1.1**, Ubuntu 26.04 LTS, kernel `7.0.0-1015-raspi`.
- **Waveshare DA7212 Audio HAT**. HAT EEPROM (`/proc/device-tree/hat/`): product `DA7212 Audio HAT`,
  vendor `waveshare Limited`, product id `0xf475`, version `0x0001`.
- Two speaker connectors (stereo), each with its own onboard amp, and an onboard microphone.
- GPIO stack order: audio HAT → Pan-Tilt HAT → Pi 5.

The HAT needs these header pins kept clear: **GPIO18–21** (I2S), **GPIO2/3** (I2C, codec at `0x1a`
on bus 1), **GPIO0/1** (HAT ID EEPROM).

### The board shows up as "RPi Codec Zero"

This is expected. The firmware reads the HAT EEPROM and loads the IQaudio codec overlay by itself
(the sound node's compatible string is `iqaudio,iqaudio-codec`), and the `da7213` kernel driver
binds to the DA7212 at `1-001a`. ALSA then lists it as:

```
card 0: Zero [RPi Codec Zero], device 0: Raspberry Pi Codec Zero HiFi da7213-hifi-0
```

Cards 1 and 2 are the two HDMI outputs. Loaded modules: `snd_soc_da7213`, `snd_soc_iqaudio_codec`,
`designware_i2s`.

The Codec Zero documentation describes a *mono* speaker output. That does not apply to this board.

## Boot configuration

`/boot/firmware/config.txt` has **no audio `dtoverlay=` line** — the overlay comes from the HAT
EEPROM. The lines that matter are the stock Ubuntu ones:

```ini
dtparam=audio=on
dtparam=i2c_arm=on
dtparam=spi=on
```

If a fresh image does not show card `Zero` in `aplay -l`, adding `dtoverlay=iqaudio-codec` under
`[all]` is the thing to try. That has not been needed or tested here.

## Sound stack

Raw ALSA only. PulseAudio, PipeWire and WirePlumber are not installed and must stay that way.

- Installed: `alsa-utils` 1.2.15.2, `libasound2t64` 1.2.15.3, `espeak`, `espeak-ng`.
- The `kepler` user is in the `audio` group (also `i2c`, `gpio`, `spi`, `dialout`).
- `alsa-restore.service` (static) reloads `/var/lib/alsa/asound.state` at boot.

**Do not use PortAudio / `sounddevice`.** Ubuntu's `libportaudio2` has a PulseAudio backend and
`Pa_Initialize` fails with no PulseAudio server, so `import sounddevice` raises. Installing
`pipewire-pulse` or `pulseaudio` to "fix" that puts a sound server between the app and the codec.
The project uses `aplay` and `arecord` instead.

## ALSA configuration files

### `~/.asoundrc`

This is the file that matters. The codec driver advertises a continuous 8000–96000 Hz range but
cannot actually run at 22050 Hz, so ALSA's `plug` passes 22050 through un-resampled and the codec
rejects it. That silently broke espeak and pyttsx3. Pinning the slave to 48000 Hz stereo makes
`plug` resample everything.

```
# Raspberry Pi Codec Zero (DA7213) playback fix.
#
# The codec driver advertises a continuous 8000-96000 Hz rate range, but the
# hardware clock can't actually produce 22050 Hz. ALSA's `plug` plugin trusts
# the advertised range and passes 22050 through un-resampled, so the device
# rejects it (this is why espeak/pyttsx3, which output 22050 Hz, were silent).
#
# Pinning the slave rate to 48000 forces `plug` to resample *everything* to a
# rate the codec genuinely supports. 24000/44100/48000 already worked; this
# just rescues 22050 and any other "claimed but unsupported" rate.
pcm.!default {
    type plug
    slave {
        pcm "hw:0,0"
        rate 48000
        channels 2
    }
}

ctl.!default {
    type hw
    card 0
}
```

### `/etc/asound.conf`

Also present, and overridden by `~/.asoundrc` for the `kepler` user. It lacks the rate pin, so it
is not enough by itself.

```
pcm.!default {
    type plug
    slave {
        pcm "hw:0,0"
    }
}

ctl.!default {
    type hw
    card 0
}
```

## Mixer

### The controls that matter

| Control | Value | Why |
|---|---|---|
| `Headphone Volume` | 38 of 63 (60%, -19 dB) | **This is the speaker volume.** Confirmed by ear. |
| `Headphone Switch` | on, on | Off means silent speakers. |
| `Lineout Volume` / `Switch` | 48 (0 dB) / on | Mono output, does not drive the speakers. |
| `DAC Volume` | 111 of 127 (-0.75 dB) | Digital level ahead of both outputs. |
| `Mixout Left DAC Left Switch` | on | Routes the DAC to the output. Off means everything is silent. |
| `Mixout Right DAC Right Switch` | on | Same, right channel. |
| `DAC Left Source MUX` / `Right` | `DAI Input Left` / `DAI Input Right` | Playback comes from the Pi. |
| `Mic 2 Switch` / `Volume` | on / 7 (+36 dB) | The onboard mic is on **Mic 2**. Mic 1 picks up nothing. |
| `Mic 2 Amp Source MUX` | `MIC_P` (index 1) | Single-ended. About 12 dB more than `Differential`. |
| `Mixin Left Mic 2 Switch` | on | `plug` takes the *left* channel for mono capture. |
| `Mixin Right Mic 2 Switch` | on | |
| `Mixin PGA Switch` / `Volume` | on, on / 3, 3 | |
| `ADC Switch` / `Volume` | on, on / 111, 111 | |

Playback chain: `DAI → DAC → Mixout → Headphone → speaker amps`.
Capture chain: `Mic 2 → Mixin → Mixin PGA → ADC → DAI`.

To change the speaker volume:

```bash
amixer -c 0 sset Headphone 60%
```

### Full mixer state

All 106 controls as they were on 2026-10-04. Replaying this block reproduces the working state
exactly and needs no root. It was replayed against the live card with no errors.

```bash
amixer -q -c 0 cset name='Headphone Gain Ramping Switch' on,on
amixer -q -c 0 cset name='Headphone ZC Switch' off,off
amixer -q -c 0 cset name='Headphone Switch' on,on
amixer -q -c 0 cset name='Headphone Volume' 38,38
amixer -q -c 0 cset name='Lineout Gain Ramping Switch' on
amixer -q -c 0 cset name='Lineout Switch' on
amixer -q -c 0 cset name='Lineout Volume' 48
amixer -q -c 0 cset name='Mic 1 Amp Source MUX' 0
amixer -q -c 0 cset name='Mic 1 Switch' off
amixer -q -c 0 cset name='Mic 1 Volume' 1
amixer -q -c 0 cset name='Mic 2 Amp Source MUX' 1
amixer -q -c 0 cset name='Mic 2 Switch' on
amixer -q -c 0 cset name='Mic 2 Volume' 7
amixer -q -c 0 cset name='Aux Gain Ramping Switch' on,on
amixer -q -c 0 cset name='Aux ZC Switch' off,off
amixer -q -c 0 cset name='Aux Switch' off,off
amixer -q -c 0 cset name='Aux Volume' 53,53
amixer -q -c 0 cset name='ADC Gain Ramping Switch' on,on
amixer -q -c 0 cset name='ADC HPF Cutoff' 0
amixer -q -c 0 cset name='ADC HPF Switch' on
amixer -q -c 0 cset name='ADC Voice Cutoff' 0
amixer -q -c 0 cset name='ADC Voice Mode Switch' off
amixer -q -c 0 cset name='ADC Switch' on,on
amixer -q -c 0 cset name='ADC Volume' 111,111
amixer -q -c 0 cset name='ALC Anticlip Level' 0
amixer -q -c 0 cset name='ALC Anticlip Mode Switch' off
amixer -q -c 0 cset name='ALC Attack Rate' 0
amixer -q -c 0 cset name='ALC Hold Time' 0
amixer -q -c 0 cset name='ALC Integ Attack Rate' 0
amixer -q -c 0 cset name='ALC Integ Release Rate' 0
amixer -q -c 0 cset name='ALC Max Analog Gain Volume' 7
amixer -q -c 0 cset name='ALC Max Attenuation Volume' 15
amixer -q -c 0 cset name='ALC Max Gain Volume' 15
amixer -q -c 0 cset name='ALC Max Threshold Volume' 63
amixer -q -c 0 cset name='ALC Min Analog Gain Volume' 1
amixer -q -c 0 cset name='ALC Min Threshold Volume' 0
amixer -q -c 0 cset name='ALC Noise Threshold Volume' 0
amixer -q -c 0 cset name='ALC Release Rate' 0
amixer -q -c 0 cset name='ALC Switch' off,off
amixer -q -c 0 cset name='AUX Jack Switch' off
amixer -q -c 0 cset name='DAC EQ Switch' off
amixer -q -c 0 cset name='DAC EQ1 Volume' 8
amixer -q -c 0 cset name='DAC EQ2 Volume' 8
amixer -q -c 0 cset name='DAC EQ3 Volume' 8
amixer -q -c 0 cset name='DAC EQ4 Volume' 8
amixer -q -c 0 cset name='DAC EQ5 Volume' 8
amixer -q -c 0 cset name='DAC Gain Ramping Switch' on,on
amixer -q -c 0 cset name='DAC HPF Cutoff' 0
amixer -q -c 0 cset name='DAC HPF Switch' on
amixer -q -c 0 cset name='DAC Invert Switch' off,off
amixer -q -c 0 cset name='DAC Left Source MUX' 2
amixer -q -c 0 cset name='DAC Mono Switch' off,off
amixer -q -c 0 cset name='DAC NG OFF Threshold' 0
amixer -q -c 0 cset name='DAC NG ON Threshold' 0
amixer -q -c 0 cset name='DAC NG Rampdown Rate' 0
amixer -q -c 0 cset name='DAC NG Rampup Rate' 0
amixer -q -c 0 cset name='DAC NG Setup Time' 0
amixer -q -c 0 cset name='DAC NG Switch' off
amixer -q -c 0 cset name='DAC Right Source MUX' 3
amixer -q -c 0 cset name='DAC Soft Mute Rate' 0
amixer -q -c 0 cset name='DAC Soft Mute Switch' off
amixer -q -c 0 cset name='DAC Voice Cutoff' 0
amixer -q -c 0 cset name='DAC Voice Mode Switch' off
amixer -q -c 0 cset name='DAC Volume' 111,111
amixer -q -c 0 cset name='DAI Left Source MUX' 0
amixer -q -c 0 cset name='DAI Right Source MUX' 1
amixer -q -c 0 cset name='DMIC Switch' off,off
amixer -q -c 0 cset name='Gain Ramping Rate' 0
amixer -q -c 0 cset name='HP Jack Switch' on
amixer -q -c 0 cset name='MIC Jack Switch' on
amixer -q -c 0 cset name='Mixin Gain Ramping Switch' on,on
amixer -q -c 0 cset name='Mixin Left Aux Left Switch' off
amixer -q -c 0 cset name='Mixin Left Mic 1 Switch' off
amixer -q -c 0 cset name='Mixin Left Mic 2 Switch' on
amixer -q -c 0 cset name='Mixin Left Mixin Right Switch' off
amixer -q -c 0 cset name='Mixin PGA Switch' on,on
amixer -q -c 0 cset name='Mixin PGA Volume' 3,3
amixer -q -c 0 cset name='Mixin PGA ZC Switch' off,off
amixer -q -c 0 cset name='Mixin Right Aux Right Switch' off
amixer -q -c 0 cset name='Mixin Right Mic 1 Switch' off
amixer -q -c 0 cset name='Mixin Right Mic 2 Switch' on
amixer -q -c 0 cset name='Mixin Right Mixin Left Switch' off
amixer -q -c 0 cset name='Mixout Left Aux Left Invert Switch' off
amixer -q -c 0 cset name='Mixout Left Aux Left Switch' off
amixer -q -c 0 cset name='Mixout Left DAC Left Switch' on
amixer -q -c 0 cset name='Mixout Left Mixin Left Invert Switch' off
amixer -q -c 0 cset name='Mixout Left Mixin Left Switch' off
amixer -q -c 0 cset name='Mixout Left Mixin Right Invert Switch' off
amixer -q -c 0 cset name='Mixout Left Mixin Right Switch' off
amixer -q -c 0 cset name='Mixout Right Aux Right Invert Switch' off
amixer -q -c 0 cset name='Mixout Right Aux Right Switch' off
amixer -q -c 0 cset name='Mixout Right DAC Right Switch' on
amixer -q -c 0 cset name='Mixout Right Mixin Left Invert Switch' off
amixer -q -c 0 cset name='Mixout Right Mixin Left Switch' off
amixer -q -c 0 cset name='Mixout Right Mixin Right Invert Switch' off
amixer -q -c 0 cset name='Mixout Right Mixin Right Switch' off
amixer -q -c 0 cset name='Onboard MIC Switch' on
amixer -q -c 0 cset name='ToneGen DTMF Key' 0
amixer -q -c 0 cset name='ToneGen DTMF Switch' off
amixer -q -c 0 cset name='ToneGen Off Time' 1
amixer -q -c 0 cset name='ToneGen On Time' 2
amixer -q -c 0 cset name='ToneGen Sinewave Gen Type' 0
amixer -q -c 0 cset name='ToneGen Sinewave1 Freq' 5461
amixer -q -c 0 cset name='ToneGen Sinewave2 Freq' 16384
amixer -q -c 0 cset name='ToneGen Start' off
amixer -q -c 0 cset name='ToneGen Volume' 0
```

### Making it survive a reboot

Mixer changes are lost on reboot until they are stored. This needs a password, so it has to be run
by hand:

```bash
sudo alsactl store
```

That writes `/var/lib/alsa/asound.state`, which `alsa-restore.service` loads at boot. As of
2026-10-04 the stored state matches the block above.

## How the project uses audio

- **Playback:** [output/audio_out.py](../output/audio_out.py) — `PcmPlayer` pipes raw PCM to
  `aplay -q -D default -f S16_LE -r <rate> -c <channels>`. Speech from
  [output/speech.py](../output/speech.py) is 24000 Hz mono.
- **Capture:** [input/recognizer.py](../input/recognizer.py) — runs
  `arecord -q -D default -f S16_LE -r 16000 -c 1 -t raw` and feeds Moonshine.
- Python dependencies are in [requirements.txt](../requirements.txt) and go in `.venv`
  (`moonshine-voice`, `google-genai`). Run things with `.venv/bin/python`.

## Reinitializing on a new SD card

1. Flash Ubuntu 26.04 for Raspberry Pi and boot with the audio HAT attached.
2. Install the tools and make sure the user can reach the sound card:

   ```bash
   sudo apt install alsa-utils espeak-ng
   ```

   ```bash
   sudo usermod -aG audio,i2c,gpio,spi,dialout kepler
   ```

   Do **not** install `pulseaudio`, `pipewire-pulse` or `libportaudio2`.
3. Check the card is detected. Card 0 should be `Zero [RPi Codec Zero]`:

   ```bash
   aplay -l
   ```

4. Create `~/.asoundrc` with the contents shown [above](#asoundrc).
5. Replay the [full mixer state](#full-mixer-state) block.
6. Store it:

   ```bash
   sudo alsactl store
   ```

7. Recreate `.venv` and install `requirements.txt`.
8. Run the [checks](#checks) below.

## Checks

Speaker, using the bundled clip:

```bash
aplay -D default output/corporate-trainer.wav
```

A 22050 Hz source, which only works if `~/.asoundrc` is in place:

```bash
espeak-ng "audio check"
```

Microphone, three seconds recorded and played back:

```bash
arecord -D default -f S16_LE -r 16000 -c 1 -d 3 /tmp/mic.wav && aplay /tmp/mic.wav
```

While something is playing, this should show `rate: 48000`, `channels: 2`:

```bash
cat /proc/asound/card0/pcm0p/sub0/hw_params
```

## Troubleshooting

**Speakers silent — check the wiring first.** Plugging the Pi+HAT stack into the HexArth ESP32
board through the full 40-pin header kills speaker output completely, with an unchanged mixer and
every software check passing. Connect the ESP32 with three wires only: pin 8 → pin 8, pin 10 →
pin 10, and a ground.

**Speakers silent, wiring fine.** The mixer has come up muted. Check `Headphone Switch` and the two
`Mixout … DAC … Switch` controls, or replay the full mixer block.

**`arecord` hangs or gives `read error: Input/output error`.** The capture path is off. While it is
off the codec does not power up for capture at all — except for about five seconds after playback,
when the codec is still clocked, which makes the fault look intermittent. Replay the mixer block.

**espeak or pyttsx3 silent while WAV files play.** `~/.asoundrc` is missing or lacks `rate 48000`.

**Speech stops after a few messages.** This is usually the Gemini TTS free-tier quota (10 requests
per day), not audio. Look for `Failed to speak` or `Rate limit` in the day's log.

**Has the mixer drifted?** Dump the live state and compare it with the stored one:

```bash
alsactl -f /tmp/now.state store 0 && diff <(sed -n '/^state.Zero/,/^}/p' /var/lib/alsa/asound.state) /tmp/now.state
```

"""Reads registers back from an ST7789 screen, to see whether commands really reach it.

    python3 -m display.readback_test right        # or left
    python3 -m display.readback_test right 200    # repeat the ID read 200 times (default 100)

SPI only ever sends, so the Pi can't tell whether a screen got anything. The ST7789 can answer
read commands on its data line (DIN/SDA), but the Pi's SPI hardware can't listen on that line, so
this drives the pins by hand, slowly. It shows:

  - the panel's ID, which is fixed. Reading it correctly proves the clock, data, CS and DC wiring.
  - the power mode before and after waking the panel. If it changes, commands are getting through.
  - how often the same ID read comes back the same, which puts a number on flakiness.

Driving the pins by hand takes GPIO10/11 out of SPI mode, and only root can put them back. Until
`sudo pinctrl set 10,11 a0` is run, or the Pi reboots, the screens can't be driven normally.
"""
import sys
import time
import lgpio

SCK = 11
MOSI = 10

# CS, DC, RST
PINS = {
    "left": (5, 23, 27),
    "right": (6, 24, 4),
}

# Commands
SLPOUT = 0x11
DISPON = 0x29
COLMOD = 0x3A
RDDID = 0x04      # 24 bits, after a dummy clock
RDDPM = 0x0A      # power mode, 8 bits
RDDCOLMOD = 0x0C  # pixel format, 8 bits
RDID1, RDID2, RDID3 = 0xDA, 0xDB, 0xDC  # one ID byte each, 8 bits

# RDDPM bits
POWER_MODE_BITS = [(7, "booster on"), (6, "idle mode"), (5, "partial mode"), (4, "awake (sleep out)"),
                   (3, "normal mode"), (2, "display on")]


class BitBangPanel:
    """Talks to one ST7789 by setting each pin by hand. Slow, but it can read as well as write."""

    def __init__(self, chip: int, cs: int, dc: int, rst: int):
        self.chip, self.cs, self.dc, self.rst = chip, cs, dc, rst
        for pin, level in ((SCK, 0), (MOSI, 0), (cs, 1), (dc, 1), (rst, 1)):
            lgpio.gpio_claim_output(chip, pin, level)

    def reset(self):
        lgpio.gpio_write(self.chip, self.rst, 0)
        time.sleep(0.02)
        lgpio.gpio_write(self.chip, self.rst, 1)
        # The panel needs up to 120ms after a reset before it takes commands
        time.sleep(0.15)

    def command(self, command: int, *params: int):
        self._select()
        self._send_byte(command)
        lgpio.gpio_write(self.chip, self.dc, 1)
        for param in params:
            self._send_byte(param)
        self._deselect()

    def read(self, command: int, bits: int, dummy_clock: bool = False) -> int:
        self._select()
        self._send_byte(command)
        # The panel answers on the same line, so stop driving it
        lgpio.gpio_free(self.chip, MOSI)
        lgpio.gpio_claim_input(self.chip, MOSI, lgpio.SET_PULL_NONE)
        try:
            if dummy_clock:
                self._clock_in(1)
            return self._clock_in(bits)
        finally:
            self._deselect()
            lgpio.gpio_free(self.chip, MOSI)
            lgpio.gpio_claim_output(self.chip, MOSI, 0)

    def close(self):
        for pin in (SCK, MOSI, self.cs, self.dc, self.rst):
            lgpio.gpio_free(self.chip, pin)

    def _select(self):
        lgpio.gpio_write(self.chip, self.dc, 0)
        lgpio.gpio_write(self.chip, self.cs, 0)

    def _deselect(self):
        lgpio.gpio_write(self.chip, self.cs, 1)

    def _send_byte(self, byte: int):
        # Mode 0, most significant bit first: the panel takes each bit as the clock rises
        for bit in range(7, -1, -1):
            lgpio.gpio_write(self.chip, MOSI, (byte >> bit) & 1)
            lgpio.gpio_write(self.chip, SCK, 1)
            lgpio.gpio_write(self.chip, SCK, 0)

    def _clock_in(self, bits: int) -> int:
        # The panel changes the line as the clock falls, so it is steady to read once the clock is high
        value = 0
        for _ in range(bits):
            lgpio.gpio_write(self.chip, SCK, 1)
            value = (value << 1) | lgpio.gpio_read(self.chip, MOSI)
            lgpio.gpio_write(self.chip, SCK, 0)
        return value


def describe_power_mode(value: int) -> str:
    on = [name for bit, name in POWER_MODE_BITS if value & (1 << bit)]
    return f"0x{value:02X} ({', '.join(on) if on else 'nothing set'})"


def looks_like_no_reply(*values: int) -> bool:
    # A line nobody drives reads as nearly all ones or nearly all zeros, with the odd bit flipped by noise.
    # A real ID has plenty of both, an ST7789V's 0x85 0x85 0x52 has 9 ones and 15 zeros.
    ones = sum(bin(v).count("1") for v in values)
    zeros = 8 * len(values) - ones
    return ones < 4 or zeros < 4


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in PINS:
        print(__doc__)
        return 1
    side = sys.argv[1]
    repeats = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    chip = lgpio.gpiochip_open(0)
    # Keep the other screen off the bus
    other_cs = PINS["left" if side == "right" else "right"][0]
    lgpio.gpio_claim_output(chip, other_cs, 1)

    panel = BitBangPanel(chip, *PINS[side])
    try:
        print(f"=== {side} screen ===")
        panel.reset()

        id_bytes = (panel.read(RDID1, 8), panel.read(RDID2, 8), panel.read(RDID3, 8))
        rddid = panel.read(RDDID, 24, dummy_clock=True)
        print(f"ID bytes (RDID1-3): {' '.join(f'0x{b:02X}' for b in id_bytes)}")
        print(f"ID (RDDID):         0x{rddid:06X}")
        replied = not looks_like_no_reply(*id_bytes)
        if not replied:
            print("  -> No reply. The screen isn't driving the data line back, so the register values below")
            print("     mean nothing. Either the module doesn't support reads on DIN, or DIN, SCK, CS or DC")
            print("     isn't reaching it. The wake commands are still sent: if the screen fills with random")
            print("     noise, they got through.")
        else:
            print("  -> The screen answered. An ST7789V usually reads 0x85 0x85 0x52, but other values are fine")
            print("     as long as they are the same every time (see the repeat test below).")

        before = panel.read(RDDPM, 8)
        print(f"\nPower mode after reset: {describe_power_mode(before)}")
        print("  (expected: asleep, display off)")

        panel.command(SLPOUT)
        time.sleep(0.15)
        panel.command(COLMOD, 0x55)
        panel.command(DISPON)
        time.sleep(0.05)

        after = panel.read(RDDPM, 8)
        colmod = panel.read(RDDCOLMOD, 8)
        print(f"Power mode after wake:  {describe_power_mode(after)}")
        print("  (expected: awake, display on. The screen should now show random noise from its memory)")
        print(f"Pixel format:           0x{colmod:02X} (expected 0x55 or 0x05, 16 bits a pixel)")
        if not replied:
            print("  -> Skipped: reads aren't working, so there's nothing to compare.")
        elif after != before and after & (1 << 4) and after & (1 << 2):
            print("  -> Commands are getting through: the panel woke up and turned its display on.")
        elif after == before:
            print("  -> Nothing changed, so the wake commands didn't reach the panel.")

        if not replied:
            return 0
        print(f"\nReading the ID {repeats} times...")
        readings = {}
        for _ in range(repeats):
            reading = (panel.read(RDID1, 8), panel.read(RDID2, 8), panel.read(RDID3, 8))
            readings[reading] = readings.get(reading, 0) + 1
        for reading, count in sorted(readings.items(), key=lambda item: -item[1]):
            print(f"  {' '.join(f'0x{b:02X}' for b in reading)}: {count} times")
        if len(readings) == 1:
            print("  -> Every read matched.")
        else:
            print(f"  -> {repeats - max(readings.values())} of {repeats} reads disagreed. "
                  f"Something on the line is unreliable, even at this slow speed.")
    finally:
        panel.close()
        lgpio.gpio_free(chip, other_cs)
        lgpio.gpiochip_close(chip)
        print("\nGPIO10/11 are no longer in SPI mode. Before using the screens normally, run:")
        print("    sudo pinctrl set 10,11 a0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Driver for the Waveshare Pan-Tilt HAT (2-DOF servo head).

The HAT carries a PCA9685 16-channel PWM chip on I2C address 0x40. Two of its
channels drive the pan (horizontal) and tilt (vertical) servos. Everything is
I2C -- no GPIO -- so this works unmodified on the Pi 5, where RPi.GPIO does not.

Angles are signed and centered, which is how a head actually thinks about
itself: 0 is looking straight ahead, pan is positive to the right, tilt is
positive up. The raw 0-180 servo range is an implementation detail.

    from head.pan_tilt import PanTiltHat

    with PanTiltHat() as head:
        head.center()
        head.look(pan=30, tilt=10)          # snap
        head.look_smooth(pan=-30, speed=45) # glide at 45 deg/sec

Leaving the `with` block relaxes both servos so they stop holding torque
(a servo under constant load buzzes and gets warm).

Enable I2C first (`sudo raspi-config` -> Interface Options -> I2C) and install
the bus library with `pip install smbus2`.

Hardware notes:
  * Per Waveshare, test the servo range *before* bolting the brackets on. A
    servo commanded past its mechanical stop will stall and cook itself. The
    default limits below are deliberately conservative -- widen them only after
    watching the real head move.
  * The 5V servo rail draws real current under load. Feed the Pi from a supply
    with headroom, or fast movements will brown out the board.
"""
from __future__ import annotations

import threading
import time

try:  # smbus2 is pure python and installs cleanly on Bookworm / Pi 5
    from smbus2 import SMBus
except ImportError:  # pragma: no cover - fall back to the older system package
    try:
        from smbus import SMBus
    except ImportError:
        SMBus = None

# --- PCA9685 registers (see datasheet section 7.3) ---
_MODE1 = 0x00
_MODE2 = 0x01
_PRESCALE = 0xFE
_LED0_ON_L = 0x06

_MODE1_RESTART = 0x80
_MODE1_SLEEP = 0x10
_MODE2_OUTDRV = 0x04  # totem pole output, required to drive servo signal lines
_FULL_OFF = 0x10  # bit 4 of LEDn_OFF_H: force the channel low, no pulses

_OSC_HZ = 25_000_000.0
_PWM_STEPS = 4096

# --- Servo timing ---
# Standard hobby servos sweep 0-180 degrees over a ~0.5-2.5ms pulse. These
# values match Waveshare's reference driver (angle * 2000/180 + 501).
PWM_FREQ_HZ = 50
_PERIOD_US = 1_000_000 // PWM_FREQ_HZ  # 20000us
MIN_PULSE_US = 501.0
MAX_PULSE_US = 2501.0

I2C_ADDRESS = 0x40
I2C_BUS = 1

# Which PCA9685 channel drives which axis. Waveshare's own demos are ambiguous
# about this and mounting varies, so verify with `python head/pan_tilt.py` and
# swap here (or pass the channels in) if the axes come out reversed.
PAN_CHANNEL = 0
TILT_CHANNEL = 1

# Conservative soft limits in signed degrees. The servos themselves accept
# +/-90, but the bracket and whatever is mounted on it will bind first.
PAN_LIMITS = (-80.0, 80.0)
TILT_LIMITS = (-40.0, 40.0)

# Step rate for interpolated moves. Matches the 50Hz servo update rate, so
# there is no point going finer.
_SMOOTH_STEP_HZ = 50


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class PanTiltHat:
    """Commands the two servos on a Waveshare Pan-Tilt HAT.

    Safe to share between threads; every I2C transaction is serialized.
    """

    def __init__(
        self,
        address: int = I2C_ADDRESS,
        bus: int = I2C_BUS,
        pan_channel: int = PAN_CHANNEL,
        tilt_channel: int = TILT_CHANNEL,
        pan_limits: tuple[float, float] = PAN_LIMITS,
        tilt_limits: tuple[float, float] = TILT_LIMITS,
        invert_pan: bool = False,
        invert_tilt: bool = False,
        pan_trim: float = 0.0,
        tilt_trim: float = 0.0,
    ):
        """
        invert_* flips an axis if the servo is mounted facing the other way.
        *_trim nudges the mechanical center (degrees) when the head sits
        slightly off-square with everything commanded to 0.
        """
        if SMBus is None:
            raise RuntimeError(
                "No I2C library found. Install one with `pip install smbus2`."
            )

        self._bus = SMBus(bus)
        self._address = address
        self._pan_channel = pan_channel
        self._tilt_channel = tilt_channel
        self._pan_limits = pan_limits
        self._tilt_limits = tilt_limits
        self._invert_pan = invert_pan
        self._invert_tilt = invert_tilt
        self._pan_trim = pan_trim
        self._tilt_trim = tilt_trim
        self._lock = threading.RLock()

        # Last commanded angles. Servos have no feedback, so this is the only
        # notion of "where the head is" available -- it is accurate as long as
        # nothing stalls or gets shoved by hand.
        self._pan = 0.0
        self._tilt = 0.0

        self._reset()

    # --- position ---

    @property
    def pan(self) -> float:
        """Last commanded pan angle, in signed degrees (positive = right)."""
        return self._pan

    @property
    def tilt(self) -> float:
        """Last commanded tilt angle, in signed degrees (positive = up)."""
        return self._tilt

    def look(self, pan: float | None = None, tilt: float | None = None) -> None:
        """Move immediately to an absolute angle. Omitted axes hold position.

        The servo takes its own sweet time getting there (roughly 0.1-0.2 sec
        per 60 degrees) and this does not wait for it. Use `look_smooth` when
        the motion itself should look deliberate.
        """
        with self._lock:
            if pan is not None:
                self._pan = _clamp(pan, *self._pan_limits)
                self._write_axis(self._pan_channel, self._pan, self._invert_pan, self._pan_trim)
            if tilt is not None:
                self._tilt = _clamp(tilt, *self._tilt_limits)
                self._write_axis(self._tilt_channel, self._tilt, self._invert_tilt, self._tilt_trim)

    def look_smooth(
        self,
        pan: float | None = None,
        tilt: float | None = None,
        speed: float = 60.0,
    ) -> None:
        """Glide to an absolute angle at `speed` degrees/sec, blocking until done.

        Both axes start and finish together, so the head follows a straight
        line rather than an L-shape. Duration is set by whichever axis has
        further to travel.
        """
        start_pan, start_tilt = self._pan, self._tilt
        end_pan = start_pan if pan is None else _clamp(pan, *self._pan_limits)
        end_tilt = start_tilt if tilt is None else _clamp(tilt, *self._tilt_limits)

        travel = max(abs(end_pan - start_pan), abs(end_tilt - start_tilt))
        if travel < 0.5 or speed <= 0:
            self.look(pan=end_pan, tilt=end_tilt)
            return

        duration = travel / speed
        steps = max(1, int(duration * _SMOOTH_STEP_HZ))
        interval = duration / steps

        for step in range(1, steps + 1):
            progress = step / steps
            self.look(
                pan=start_pan + (end_pan - start_pan) * progress,
                tilt=start_tilt + (end_tilt - start_tilt) * progress,
            )
            time.sleep(interval)

    def nudge(self, pan: float = 0.0, tilt: float = 0.0) -> None:
        """Move relative to where the head currently is."""
        self.look(pan=self._pan + pan, tilt=self._tilt + tilt)

    def center(self, smooth: bool = False, speed: float = 60.0) -> None:
        """Return to looking straight ahead."""
        if smooth:
            self.look_smooth(pan=0.0, tilt=0.0, speed=speed)
        else:
            self.look(pan=0.0, tilt=0.0)

    # --- power ---

    def relax(self) -> None:
        """Cut the pulse train so the servos go slack and stop drawing current.

        The head will droop under its own weight. Any later `look` re-engages
        them. Worth doing whenever the head will sit still for a while -- a
        loaded servo buzzes, heats up, and jitters.
        """
        with self._lock:
            for channel in (self._pan_channel, self._tilt_channel):
                self._write(_LED0_ON_L + 4 * channel + 3, _FULL_OFF)

    def close(self) -> None:
        """Relax the servos and release the I2C bus."""
        with self._lock:
            if self._bus is None:
                return
            try:
                self.relax()
            finally:
                self._bus.close()
                self._bus = None

    def __enter__(self) -> "PanTiltHat":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # --- PCA9685 plumbing ---

    def _reset(self) -> None:
        """Wake the chip, set the servo PWM frequency, and park at center."""
        with self._lock:
            self._write(_MODE1, 0x00)
            self._set_pwm_freq(PWM_FREQ_HZ)
            self.center()

    def _set_pwm_freq(self, freq_hz: int) -> None:
        """Set the PWM prescaler. The chip must sleep while PRE_SCALE changes."""
        prescale = round(_OSC_HZ / (_PWM_STEPS * freq_hz)) - 1

        old_mode = self._read(_MODE1)
        self._write(_MODE1, (old_mode & ~_MODE1_RESTART) | _MODE1_SLEEP)
        self._write(_PRESCALE, prescale)
        self._write(_MODE1, old_mode)
        time.sleep(0.005)  # oscillator needs 500us to stabilize before RESTART
        self._write(_MODE1, old_mode | _MODE1_RESTART)
        self._write(_MODE2, _MODE2_OUTDRV)

    def _write_axis(self, channel: int, angle: float, invert: bool, trim: float) -> None:
        """Convert a signed angle to a servo pulse and push it to `channel`."""
        commanded = -angle if invert else angle
        servo_angle = _clamp(90.0 + commanded + trim, 0.0, 180.0)

        pulse_us = MIN_PULSE_US + (MAX_PULSE_US - MIN_PULSE_US) * (servo_angle / 180.0)
        off = int(pulse_us * _PWM_STEPS / _PERIOD_US)

        base = _LED0_ON_L + 4 * channel
        self._write(base + 0, 0)  # ON_L  -- pulse always starts at count 0
        self._write(base + 1, 0)  # ON_H
        self._write(base + 2, off & 0xFF)  # OFF_L
        self._write(base + 3, off >> 8)  # OFF_H (also clears the full-off bit)

    def _write(self, register: int, value: int) -> None:
        with self._lock:
            self._bus.write_byte_data(self._address, register, value)

    def _read(self, register: int) -> int:
        with self._lock:
            return self._bus.read_byte_data(self._address, register)


if __name__ == "__main__":
    # Calibration pass. Run with the brackets loose (or off) the first time and
    # confirm each axis moves the way it is labeled. If pan and tilt are
    # swapped, exchange PAN_CHANNEL and TILT_CHANNEL above; if an axis runs
    # backwards, pass invert_pan=True / invert_tilt=True.
    with PanTiltHat() as head:
        print("center")
        head.center()
        time.sleep(1)

        for label, kwargs in [
            ("pan right", {"pan": 45}),
            ("pan left", {"pan": -45}),
            ("pan center", {"pan": 0}),
            ("tilt up", {"tilt": 25}),
            ("tilt down", {"tilt": -25}),
            ("tilt center", {"tilt": 0}),
        ]:
            print(label)
            head.look_smooth(**kwargs, speed=45)
            time.sleep(0.5)

        print("relaxing")

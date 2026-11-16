from importlib import _bootstrap_external
from display.display_state import DisplayState, EyeState
from display import graphics
import logging
import random

def calc_degrees_progressed(seconds_elapsed: float, rpm_speed: float):
   minutes_elapsed = seconds_elapsed / 60
   rotations = rpm_speed * minutes_elapsed
   return rotations * 360

EYE_COLORS = {
   EyeState.REGULAR: '#067BC1',
   EyeState.SPEAKING: '#679436',
   EyeState.BOOTING: '#E1EFFF',
   EyeState.ERROR: '#FF6B6B',
}
EYE_COLOR_FADE_SECONDS = 0.4

PUPIL_RADIUS = 37
IRIS_RADIUS = 15

# While booting every orbit sits on this one ring, half way across the solid part of the iris
BOOTING_ORBIT_DIAMETER = 2 * (PUPIL_RADIUS + IRIS_RADIUS / 2)
ORBIT_EXPAND_SECONDS = 0.8

class PlanetEyeScenario:
   def __init__(self):
      self.eye_color = EYE_COLORS[EyeState.BOOTING]
      # The eye fades from one color to the next, the amount goes from 0 to 1 over the fade time
      self.fade_from_color = self.eye_color
      self.fade_to_color = self.eye_color
      self.fade_amount = 1.0
      self.eye_state = EyeState.BOOTING
      # 0 is every orbit pulled in behind the iris, as when booting, and 1 is every orbit at its usual size
      # Starts pulled in so the planets move out from the middle once the eye has opened
      self.orbit_expansion = 0.0
      self.planets = [
         Planet(8, 160, 8, '#B71C1C'),
         Planet(210, 190, 12, '#DA6849'),
         Planet(85, 230, 7, '#0277BD'),
      ]
      self.loader = Loader()
      self.blinker = Blinker()

   def update(self, display_state: DisplayState, seconds_elapsed: float):
      for planet in self.planets:
         planet.update(seconds_elapsed)
      self.loader.update(seconds_elapsed)
      self.blinker.update(seconds_elapsed)

      for planet in self.planets:
         planet.set_attention(display_state.at_attention)
      # Booting counts as loading, so the loader spins until startup is done
      self.loader.set_loading(display_state.is_loading or display_state.eye_state == EyeState.BOOTING)

      self.eye_state = display_state.eye_state
      if self.eye_state == EyeState.BOOTING or self.blinker.is_waking():
         self.orbit_expansion = 0.0
      else:
         self.orbit_expansion = min(1.0, self.orbit_expansion + seconds_elapsed / ORBIT_EXPAND_SECONDS)

      target_color = EYE_COLORS[display_state.eye_state]
      if target_color != self.fade_to_color:
         # Start from whatever is showing now, so a change part way through a fade does not jump
         self.fade_from_color = self.eye_color
         self.fade_to_color = target_color
         self.fade_amount = 0.0

      self.fade_amount = min(1.0, self.fade_amount + seconds_elapsed / EYE_COLOR_FADE_SECONDS)
      self.eye_color = graphics.blend_colors(self.fade_from_color, self.fade_to_color, self.fade_amount)

   def get_frame(self):
      base_image, draw = graphics.new_frame()

      # The planets go down first, so the eye is drawn over them and they pass behind the iris
      # Nothing orbits a broken eye, and pulled all the way in the planets are hidden until they start moving out,
      # since the iris does not cover them while the eye is shut
      if self.eye_state != EyeState.ERROR and self.orbit_expansion > 0:
         for planet in self.planets:
            graphics.draw_planet_orbit(draw, self.get_orbit_diameter(planet), planet.position, planet.size, planet.color)

      blink = self.blinker.get_closed_amount()
      graphics.draw_eye(base_image, 35, IRIS_RADIUS, PUPIL_RADIUS, 160, color=self.eye_color, blink=blink)

      # The loader sits in the pupil, so it goes under the lid and blinks with the eye
      if self.loader.should_draw_loader():
         loader = self.loader
         graphics.draw_under_lid(base_image, lambda layer_draw: graphics.draw_loader(
            layer_draw, loader.radius, loader.width, loader.segments, loader.buffer, loader.position,
            loader.trans_in, loader.trans_out, loader.trans_out_roller, erase_color=(0, 0, 0, 0)), blink)

      return base_image

   def get_orbit_diameter(self, planet):
      # Eased, so the orbits start and finish their move outwards gently
      eased = self.orbit_expansion * self.orbit_expansion * (3 - 2 * self.orbit_expansion)
      return round(BOOTING_ORBIT_DIAMETER + (planet.orbit_diameter - BOOTING_ORBIT_DIAMETER) * eased)
      

# class Eye:
#    def __init__(self):

class Planet:
   def __init__(self, position: float, orbit_diameter: int, size: int, color: str):
      self.position = position
      self.orbit_diameter = orbit_diameter
      self.size = size
      self.color = color

      self.at_attention = False
      self.moving_to_attention = False
      self.moving_from_attention = False
      self.seconds_to_attention = 0.5
      self.attention_position = 90
      self.attention_speed_rpm = None
      self.previous_position = None

      min_radius = 150
      max_radius = 240
      min_rpm = 0.1
      max_rpm = 5

      radius_range = max_radius - min_radius
      relative_radius = orbit_diameter - min_radius
      scalar = (radius_range - relative_radius) / radius_range
      self.rpm_speed = scalar * (max_rpm - min_rpm) + min_rpm

   def set_attention(self, attention: bool):
      if self.at_attention == attention:
         return
      self.at_attention = attention
      self.moving_to_attention = attention
      self.moving_from_attention = not attention

      if attention:
         self.position %= 360
         if self.position > 270:
            self.position -= 360
         distance = 90 - self.position
         self.previous_position = self.position

         speed_deg_sec = distance / self.seconds_to_attention
         self.attention_speed_rpm = speed_deg_sec / 6


   def update(self, seconds_elapsed: float):
      if self.moving_to_attention:
         degrees_progressed = calc_degrees_progressed(seconds_elapsed, self.attention_speed_rpm)
         self.position += degrees_progressed
         if (self.attention_speed_rpm > 0 and self.position >= self.attention_position) or (self.attention_speed_rpm < 0 and self.position <= self.attention_position):
            self.position = self.attention_position
            self.moving_to_attention = False
      elif self.moving_from_attention:
         degrees_progressed = calc_degrees_progressed(seconds_elapsed, self.attention_speed_rpm)
         self.position -= degrees_progressed
         # print('moving from', degrees_progressed, self.position, self.attention_speed_rpm)
         if (self.attention_speed_rpm < 0 and self.position >= self.previous_position) or (self.attention_speed_rpm > 0 and self.position <= self.previous_position):
            self.position = self.previous_position
            self.moving_from_attention = False
      elif self.at_attention:
         return
      else:
         degrees_progressed = calc_degrees_progressed(seconds_elapsed, self.rpm_speed)
         # print(f'updating planet position {self.rpm_speed:0.2f}, {self.position:0.2f}, {seconds_elapsed:0.2f}, {degrees_progressed:0.2f}')
         self.position += degrees_progressed


# A blink sweeps the lid down, holds it shut for a moment and sweeps it back up, about 150ms in all
BLINK_CLOSE_SECONDS = 0.06
BLINK_SHUT_SECONDS = 0.02
BLINK_OPEN_SECONDS = 0.07
BLINK_SECONDS = BLINK_CLOSE_SECONDS + BLINK_SHUT_SECONDS + BLINK_OPEN_SECONDS
# How long the eye stays open between blinks, picked at random each time
BLINK_MIN_INTERVAL_SECONDS = 3.0
BLINK_MAX_INTERVAL_SECONDS = 6.0
# Some blinks are a quick double, the second one starting this long after the first has opened
DOUBLE_BLINK_CHANCE = 0.2
DOUBLE_BLINK_GAP_SECONDS = 0.1
# On starting up the eye begins shut, stays shut for a moment, then opens more slowly than a blink, like waking up
WAKE_SHUT_SECONDS = 0.3
WAKE_OPEN_SECONDS = 0.35


class Blinker:
   """
   Closes the eye now and then, at random so it does not look mechanical.
   """
   def __init__(self):
      # Seconds into waking up, or None once the eye has opened for the first time
      self.wake_time = 0.0
      # Seconds into the current blink, or None while the eye is open between blinks
      self.blink_time = None
      self.seconds_until_blink = self.pick_interval()
      # Whether another blink follows straight after this one
      self.double_pending = False
      # Whether the next blink to start is the second of a double, which is never itself doubled
      self.next_is_second = False

   def pick_interval(self):
      return random.uniform(BLINK_MIN_INTERVAL_SECONDS, BLINK_MAX_INTERVAL_SECONDS)

   def is_waking(self):
      """Whether the eye is still opening for the first time since starting up."""
      return self.wake_time is not None

   def update(self, seconds_elapsed: float):
      if self.wake_time is not None:
         self.wake_time += seconds_elapsed
         if self.wake_time >= WAKE_SHUT_SECONDS + WAKE_OPEN_SECONDS:
            self.wake_time = None
         # The wait for the first blink starts once the eye is open
         return

      if self.blink_time is not None:
         self.blink_time += seconds_elapsed
         if self.blink_time >= BLINK_SECONDS:
            self.blink_time = None
            self.next_is_second = self.double_pending
            self.seconds_until_blink = DOUBLE_BLINK_GAP_SECONDS if self.double_pending else self.pick_interval()
         return

      self.seconds_until_blink -= seconds_elapsed
      if self.seconds_until_blink <= 0:
         self.blink_time = 0.0
         self.double_pending = not self.next_is_second and random.random() < DOUBLE_BLINK_CHANCE
         self.next_is_second = False

   def get_closed_amount(self):
      """
      How far the lid is closed, 0 is open and 1 is shut, eased so it speeds up and slows down like a real lid.
      """
      if self.wake_time is not None:
         amount = 1.0 - (self.wake_time - WAKE_SHUT_SECONDS) / WAKE_OPEN_SECONDS
      elif self.blink_time is None:
         return 0.0
      elif self.blink_time < BLINK_CLOSE_SECONDS:
         amount = self.blink_time / BLINK_CLOSE_SECONDS
      elif self.blink_time < BLINK_CLOSE_SECONDS + BLINK_SHUT_SECONDS:
         amount = 1.0
      else:
         amount = 1.0 - (self.blink_time - BLINK_CLOSE_SECONDS - BLINK_SHUT_SECONDS) / BLINK_OPEN_SECONDS
      amount = min(1.0, max(0.0, amount))
      return amount * amount * (3 - 2 * amount)


class Loader:
   def __init__(self):
      self.loading = False
      # spinning turns off after loading is set to false and last spin finishes
      self.spinning = False
      self.position = 0.0
      self.trans_in = True
      self.trans_out = False
      self.trans_out_roller = 0.0

      self.segments = [160, 60, 25]
      self.buffer = 20
      self.snake_length = sum(self.segments) + self.buffer * 2
      if self.snake_length >= 360:
         raise Exception("Loader snake length is over 360")

      self.radius = 27
      self.width = 7
      self.rpm_speed = 60

      # draw_loader(draw, 27, 7, 45, False, True)

   def should_draw_loader(self):
      return self.spinning

   def set_loading(self, loading: bool):
      if loading == self.loading:
         return
      elif loading:
         self.start_loading()
      else:
         self.stop_loading()

   def start_loading(self):
      if self.loading:
         return

      # print('start loading')
      if not self.spinning:
         self.position = 0.0
         self.trans_in = True
      self.trans_out = False
      self.spinning = True
      self.loading = True

   def stop_loading(self):
      if not self.loading:
         return

      # print('stop loading')
      self.loading = False

   def update(self, seconds_elapsed: float):
      if not self.spinning:
         return

      degrees_progressed = calc_degrees_progressed(seconds_elapsed, self.rpm_speed)
      self.position += degrees_progressed
      self.position %= 360

      if self.trans_in and self.position > self.snake_length:
         self.trans_in = False

      if self.trans_out and self.trans_out_roller >= 360:
         self.spinning = False
      elif self.trans_out:
         self.trans_out_roller += degrees_progressed
      elif not self.loading and self.position > self.snake_length:
         self.trans_out = True
         self.trans_out_roller = 0.0

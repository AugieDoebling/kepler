from importlib import _bootstrap_external
from display_state import DisplayState
import graphics

def calc_degrees_progressed(seconds_elapsed: float, rpm_speed: float):
   minutes_elapsed = seconds_elapsed / 60
   rotations = rpm_speed * minutes_elapsed
   return rotations * 360

class PlanetEyeScenario:
   def __init__(self):
      self.planets = [
         Planet(8, 160, 8, '#B71C1C'),
         Planet(210, 190, 12, '#DA6849'),
         Planet(85, 230, 7, '#0277BD'),
      ]
      self.loader = Loader()

   def update(self, display_state: DisplayState, seconds_elapsed: float):
      for planet in self.planets:
         planet.update(seconds_elapsed)
      self.loader.update(seconds_elapsed)

      for planet in self.planets:
         planet.set_attention(display_state.at_attention)
      self.loader.set_loading(display_state.is_loading)

   def get_frame(self):
      base_image, draw = graphics.new_frame()
      graphics.draw_eye(base_image, 35, 15, 160)

      if self.loader.should_draw_loader():
         graphics.draw_loader(draw, self.loader.radius, self.loader.width, self.loader.segments, self.loader.buffer, self.loader.position, self.loader.trans_in, self.loader.trans_out, self.loader.trans_out_roller)

      for planet in self.planets:
         graphics.draw_planet_orbit(draw, planet.orbit_diameter, planet.position, planet.size, planet.color)

      return base_image
      

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
         # print('updating planet position', self.rpm_speed, self.position, seconds_elapsed, degrees_progressed)
         self.position += degrees_progressed


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

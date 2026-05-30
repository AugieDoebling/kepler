import time
import graphics
from display_state import PlanetEyeState

FRAME_RATE = 30
FRAME_INTERVAL = 1.0 / FRAME_RATE

FRAME_BUFFER = []

def render_planet_eye(planet_eye_state: PlanetEyeState):
   base_image, draw = graphics.new_frame()

   graphics.draw_eye(base_image, 35, 15, 160)

   if planet_eye_state.loader.should_draw_loader():
      loader = planet_eye_state.loader
      graphics.draw_loader(draw, loader.radius, loader.width, loader.segments, loader.buffer, loader.position, loader.trans_in, loader.trans_out, loader.trans_out_roller)

   for planet in planet_eye_state.planets:
      graphics.draw_planet_orbit(draw, planet.orbit_diameter, planet.position, planet.size, planet.color)

   FRAME_BUFFER.append(base_image)

def display_main():
   current_state = PlanetEyeState()
   last_frame_render_time = time.perf_counter()

   for frame_number in range(FRAME_RATE * 4):
      start_time = time.perf_counter()

      if frame_number == 5:
         current_state.set_attention(True)
      if frame_number == 60:
         current_state.set_attention(False)

      current_state.update(time.perf_counter()-last_frame_render_time)
      render_planet_eye(current_state)

      frame_generated_time = time.perf_counter()
      last_frame_render_time = frame_generated_time
      elapsed_time = frame_generated_time - start_time
      sleep_time = max(0, FRAME_INTERVAL - elapsed_time)
      print(f"frame_generated_time: {elapsed_time*1000:03.04f} milliseconds, waiting {sleep_time*1000:03.04f} milliseconds")

      time.sleep(sleep_time)

   for frame_number, frame in enumerate(FRAME_BUFFER):
      frame.save(f"test_outputs/frame_{frame_number:04d}.png")


if __name__ == "__main__":
   display_main()
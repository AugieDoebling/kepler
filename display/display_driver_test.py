import time
import busio
import board
import digitalio
from display.planet_scenario import PlanetEyeScenario
from display.display_state import DisplayState
from adafruit_rgb_display import st7789
from PIL import Image, ImageDraw, ImageFont

# 1. Initialize SPI
spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs_pin = digitalio.DigitalInOut(board.D5)
dc_pin = digitalio.DigitalInOut(board.D24)
reset_pin = digitalio.DigitalInOut(board.D26)

# --- NEW: MANUALLY REBOOT THE SCREEN AND WAIT ---
# Force the reset pin low to reboot the screen, then high to wake it up
reset_pin.switch_to_output(value=False)
time.sleep(1) # Hold reset for 100ms
reset_pin.value = True
time.sleep(1) # Give the screen half a second to fully boot up!
# ------------------------------------------------

# 2. Configure display parameters
BAUDRATE = 16_000_000
display = st7789.ST7789(
    spi, cs=cs_pin, dc=dc_pin, rst=reset_pin,
    baudrate=BAUDRATE, width=240, height=284, x_offset=0, y_offset=36
)

update_time = time.perf_counter()
tenth_frame = time.perf_counter()

planets = PlanetEyeScenario()
state = DisplayState()

for frame in range(500):


    if frame == 50:
        state.set_attention(True)
    if frame == 150:
        state.set_attention(False)


    img_creation_time = time.perf_counter()
    
    planets.update(state, img_creation_time-update_time)
    image = planets.get_frame()
    update_time = img_creation_time

    img_finish_time = time.perf_counter()

    # 5. Push the image to the screen
    display.image(image)

    display_write_time = time.perf_counter()
    last_frame_time = display_write_time

    print(f'   frame {frame} - render {img_finish_time-img_creation_time:.2f}, write {display_write_time-img_finish_time:.2f}, total {display_write_time-img_creation_time:.2f}')

    if frame % 10 == 0:
        now = time.perf_counter()
        elapsed = now - tenth_frame
        tenth_frame = now

        frame_speed = elapsed / 10
        print(f'10 frames in {elapsed:.2f}, avg {frame_speed:.2f}, fps {1/frame_speed:.2f}')
import time
import busio
import board
import digitalio
from adafruit_rgb_display import st7789
from PIL import Image, ImageDraw, ImageFont

# 1. Initialize SPI
spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs_pin = digitalio.DigitalInOut(board.D5)
dc_pin = digitalio.DigitalInOut(board.D24)
reset_pin = digitalio.DigitalInOut(board.D27)

# # --- NEW: MANUALLY REBOOT THE SCREEN AND WAIT ---
# # Force the reset pin low to reboot the screen, then high to wake it up
# reset_pin.switch_to_output(value=False)
# time.sleep(0.1) # Hold reset for 100ms
# reset_pin.value = True
# time.sleep(0.5) # Give the screen half a second to fully boot up!
# ------------------------------------------------

# 2. Configure display parameters
BAUDRATE = 24000000
display = st7789.ST7789(
    spi, cs=cs_pin, dc=dc_pin, rst=reset_pin,
    baudrate=BAUDRATE, width=240, height=284, x_offset=0, y_offset=40
)

# 3. Create a Pillow Image Buffer
image = Image.new("RGB", (display.width, display.height))
draw = ImageDraw.Draw(image)

# 4. Draw graphics
draw.rectangle((0, 0, display.width, display.height), outline=0, fill=(0, 0, 0)) # Clear screen to black
# draw.rectangle((1, 1, 239, 283), outline=(255, 0, 0), fill=(0, 0, 255)) # Draw blue rect with red border

draw.rectangle((10, 10, 20, 20), outline=0, fill=(255, 0, 0))
draw.rectangle((220, 254, 230, 264), outline=0, fill=(0, 255, 0))
draw.rectangle((10, 254, 20, 264), outline=0, fill=(0, 0, 255))
draw.rectangle((220, 10, 230, 20), outline=0, fill=(255, 255, 255))

draw.rectangle((110, 130, 132, 152), outline=0, fill=(255, 255, 0))




# # # Draw some text
draw.text((30, 100), "Hello, SPI Display!", fill=(255, 255, 255))

# 5. Push the image to the screen
display.image(image)
time.sleep(5)
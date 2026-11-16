from PIL import Image, ImageColor, ImageDraw, ImageOps
import colorsys
import functools
import numpy as np
import math

RESOLUTION = (240, 284)
CENTER = (round(RESOLUTION[0] / 2), round(RESOLUTION[1] / 2))

DEBUG_LOGGING = False

def debug(*args, **kwargs):
   if DEBUG_LOGGING:
      print(*args, **kwargs)

def get_bounding_box(tl_point: tuple, size: tuple):
   return (
      round(tl_point[0]),
      round(tl_point[1]),
      round(tl_point[0] + size[0]),
      round(tl_point[1] + size[1]),
   )


def get_surrounding_bounding_box(center_point: tuple, size: tuple):
   return (
      round(center_point[0] - (size[0] / 2)),
      round(center_point[1] - (size[1] / 2)),
      round(center_point[0] + (size[0] / 2)),
      round(center_point[1] + (size[1] / 2)),
   )


def get_centered_bounding_box(size: tuple):
   tl_x = round((RESOLUTION[0] - size[0]) / 2)
   tl_y = round((RESOLUTION[1] - size[1]) / 2)
   return tl_x, tl_y, tl_x + size[0], tl_y + size[1]


def get_radial_point(angle: int, radius: float):
   x_offset = round(math.cos(math.radians(angle)) * radius)
   y_offset = round(math.sin(math.radians(angle)) * radius)
   debug('x_offset', x_offset, 'y_offset', y_offset)

   return CENTER[0] + x_offset, CENTER[1] + y_offset


def create_radial_alpha_mask(width, pupil_radius, iris_radius):
   """
   Creates a Pillow Image (mode 'L') containing a radial gradient mask.
   - Inside inner_radius: Solid white (255)
   - Between inner and outer: Smooth gradient
   - Outside outer_radius: Solid black (0)
   """
   center_x = center_y = outer_radius = width // 2
   inner_radius = iris_radius + pupil_radius

   # Create a grid of x and y coordinates
   Y, X = np.ogrid[:width, :width]

   # Calculate the distance from the center for each pixel
   dist_from_center = np.sqrt((X - center_x) ** 2 + (Y - center_y) ** 2)

   # Map the distances to a 0.0 - 1.0 range based on our radii
   # We subtract the inner_radius so the fade starts exactly at that boundary
   fade_range = outer_radius - inner_radius
   normalized_dist = (dist_from_center - inner_radius) / fade_range

   # Clip values to ensure nothing goes outside the 0.0 - 1.0 bounds
   normalized_dist = np.clip(normalized_dist, 0, 1)

   # Invert so the inside is 1.0 (opaque) and the outside is 0.0 (transparent)
   alpha_mask = 1.0 - normalized_dist

   # # Punch out the center: override anything inside the inner_radius to be 0
   alpha_mask[dist_from_center < pupil_radius] = 0.0

   # Convert to 8-bit image data (0-255)
   alpha_mask_8bit = (alpha_mask * 255).astype(np.uint8)

   # Return as a Pillow Image in 'L' (luminance/grayscale) mode
   return Image.fromarray(alpha_mask_8bit, mode='L')

# How the dark end of the eye's gradient relates to its main color, measured from '#4937A2' and '#30224B'
SHADE_HUE_SHIFT_DEGREES = 10.5
SHADE_SATURATION_SCALE = 0.83
SHADE_BRIGHTNESS_SCALE = 0.463

def get_shade(color: str):
   """
   The darker, slightly duller color that the eye fades to, worked out from its main color.
   """
   red, green, blue = ImageColor.getrgb(color)[:3]
   hue, saturation, brightness = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)

   shade = colorsys.hsv_to_rgb(
      (hue + SHADE_HUE_SHIFT_DEGREES / 360) % 1.0,
      saturation * SHADE_SATURATION_SCALE,
      brightness * SHADE_BRIGHTNESS_SCALE,
   )
   return '#{:02X}{:02X}{:02X}'.format(*(round(channel * 255) for channel in shade))


def blend_colors(from_color: str, to_color: str, amount: float):
   """
   The color part way between two colors, 0 is the first color and 1 is the second.
   """
   start = ImageColor.getrgb(from_color)[:3]
   end = ImageColor.getrgb(to_color)[:3]
   return '#{:02X}{:02X}{:02X}'.format(*(round(a + (b - a) * amount) for a, b in zip(start, end)))


# The iris pattern is tuned for a 160 pixel eye, every size in pixels below is scaled to the eye's real width
IRIS_PATTERN_DESIGN_WIDTH = 160
# Fixed so the pattern is the same every time the robot starts
IRIS_PATTERN_SEED = 1

# Strands running out from the pupil: a fine set over a coarser set, how many go around the eye and how blurred each is
IRIS_FINE_STRANDS = 420
IRIS_COARSE_STRANDS = 140
IRIS_FINE_STRAND_WEIGHT = 0.6
# How far a strand wanders from straight, in strand widths
IRIS_STRAND_WANDER = 1.0

# The bright wavy ring part way out from the pupil (the collarette): its radius, how far it wavers and how many waves
COLLARETTE_RADIUS = 49
COLLARETTE_WAVER = 3
COLLARETTE_WAVES = 40
COLLARETTE_THICKNESS = 1.4
COLLARETTE_BRIGHTNESS = 0.3
# Between the pupil and the collarette the iris is darker and its strands finer
INNER_IRIS_DARKNESS = 0.45
INNER_IRIS_STRANDS = 600

# Dark pits just outside the collarette (crypts): how many, where they sit and how dark they are
CRYPT_COUNT = 16
CRYPT_INNER_RADIUS = 52
CRYPT_OUTER_RADIUS = 64
CRYPT_DARKNESS = 0.55

# The outer edge of the iris darkens into a ring (the limbal ring) and then fades softly into the background
LIMBAL_RING_WIDTH = 12
LIMBAL_RING_DARKNESS = 0.7
OUTER_FADE_WIDTH = 10

# How the iris pattern's brightness, 0 to 1, maps onto colors worked out from the eye's color
def get_iris_palette(color: str):
   shade = get_shade(color)
   return [
      (0.0, blend_colors(shade, '#000000', 0.6)),
      (0.35, shade),
      (0.6, color),
      (0.82, blend_colors(color, '#FFFFFF', 0.3)),
      (1.0, blend_colors(color, '#FFFFFF', 0.7)),
   ]


def smooth_noise_around_circle(count: int, blur: float, rng):
   """
   Random values from 0 to 1 spaced evenly around a circle, blurred so neighbours are similar and the end joins the start.
   """
   values = rng.standard_normal(count)
   offsets = np.arange(-math.ceil(3 * blur), math.ceil(3 * blur) + 1)
   kernel = np.exp(-0.5 * (offsets / blur) ** 2)
   kernel /= kernel.sum()
   # Wrap the ends around before blurring so there is no seam where the circle closes
   padded = np.concatenate([values[-len(kernel):], values, values[:len(kernel)]])
   values = np.convolve(padded, kernel, 'same')[len(kernel):-len(kernel)]
   return (values - values.min()) / (values.max() - values.min())


def sample_around_circle(noise, turns):
   """
   Looks up noise from smooth_noise_around_circle at a share of a full turn, blending between neighbouring values.
   """
   position = (turns % 1.0) * len(noise)
   below = position.astype(int) % len(noise)
   above = (below + 1) % len(noise)
   amount = position - np.floor(position)
   return noise[below] * (1 - amount) + noise[above] * amount


def get_iris_strands(turns, radius, count: int, blur: float, rng):
   """
   Brightness from 0 to 1 of strands running out from the pupil, each wandering a little from side to side.
   """
   strands = smooth_noise_around_circle(count, blur, rng)
   wander_phase = sample_around_circle(smooth_noise_around_circle(64, 3, rng), turns) * 6
   wandering_turns = turns + IRIS_STRAND_WANDER * np.sin(radius * 0.25 + wander_phase) / count
   return sample_around_circle(strands, wandering_turns)


def get_iris_crypts(angle, radius, scale: float, rng):
   """
   How dark each pixel is from the crypts, 0 is untouched and 1 is the middle of a crypt.
   Each crypt is a soft oval stretched along the line out from the pupil.
   """
   darkness = np.zeros_like(radius)
   for _ in range(CRYPT_COUNT):
      crypt_angle = rng.uniform(-math.pi, math.pi)
      crypt_radius = rng.uniform(CRYPT_INNER_RADIUS, CRYPT_OUTER_RADIUS) * scale
      # Distance around the circle from the crypt's middle, in pixels
      across = np.angle(np.exp(1j * (angle - crypt_angle))) * radius
      along = radius - crypt_radius
      spread = (across / (rng.uniform(1.5, 3.0) * scale)) ** 2 + (along / (rng.uniform(5.0, 9.0) * scale)) ** 2
      darkness = np.maximum(darkness, np.exp(-spread))
   return darkness


@functools.lru_cache(maxsize=4)
def get_iris_pattern(width: int, pupil_radius: float):
   """
   The iris's pattern, worked out once for each size since it never changes, only its color does.
   Returns its brightness from 0 to 1, how much each pixel is darkened by the limbal ring, and how solid each pixel is.
   """
   rng = np.random.default_rng(IRIS_PATTERN_SEED)
   scale = width / IRIS_PATTERN_DESIGN_WIDTH
   outer_radius = width / 2

   Y, X = np.ogrid[:width, :width]
   x = X + 0.5 - outer_radius
   y = Y + 0.5 - outer_radius
   radius = np.sqrt(x ** 2 + y ** 2)
   angle = np.arctan2(y, x)
   turns = (angle + math.pi) / (2 * math.pi)
   # 0 at the edge of the pupil and 1 at the outer edge of the iris
   across_iris = np.clip((radius - pupil_radius) / (outer_radius - pupil_radius), 0, 1)

   fine = get_iris_strands(turns, radius / scale, IRIS_FINE_STRANDS, 1.0, rng)
   coarse = get_iris_strands(turns, radius / scale, IRIS_COARSE_STRANDS, 1.2, rng)
   strands = IRIS_FINE_STRAND_WEIGHT * fine + (1 - IRIS_FINE_STRAND_WEIGHT) * coarse
   brightness = 0.25 + 0.7 * strands ** 1.4

   # Brightest in a band just outside the collarette, dimmer towards the outer edge
   brightness *= 0.8 + 0.35 * np.exp(-((across_iris - 0.35) / 0.3) ** 2)

   collarette_waver = sample_around_circle(smooth_noise_around_circle(COLLARETTE_WAVES, 2, rng), turns) - 0.5
   collarette_radius = (COLLARETTE_RADIUS + COLLARETTE_WAVER * 2 * collarette_waver) * scale
   brightness += COLLARETTE_BRIGHTNESS * np.exp(-((radius - collarette_radius) / (COLLARETTE_THICKNESS * scale)) ** 2)

   inner_strands = get_iris_strands(turns, radius / scale, INNER_IRIS_STRANDS, 1.0, rng)
   inner_brightness = 1 - INNER_IRIS_DARKNESS + 0.3 * inner_strands
   brightness = np.where(radius < collarette_radius, brightness * inner_brightness, brightness)

   brightness *= 1 - CRYPT_DARKNESS * get_iris_crypts(angle, radius, scale, rng)
   brightness = np.clip(brightness, 0, 1)

   limbal_start = outer_radius - LIMBAL_RING_WIDTH * scale
   limbal = 1 - LIMBAL_RING_DARKNESS * np.clip((radius - limbal_start) / (LIMBAL_RING_WIDTH * scale), 0, 1)

   # Soft outside so the iris fades into the background, and a crisp but smoothed edge around the hollow pupil
   alpha = np.clip((outer_radius - radius) / (OUTER_FADE_WIDTH * scale), 0, 1)
   alpha *= np.clip(radius - pupil_radius + 0.5, 0, 1)

   for array in (brightness, limbal, alpha):
      array.setflags(write=False)
   return brightness, limbal, alpha


# The upper lid's edge is the bottom of an ellipse, sized from the eye's width so the edge curves down in the middle
UPPER_LID_WIDTH_SCALE = 1.4
UPPER_LID_HEIGHT_SCALE = 1.2
# How far past the bottom of the eye the middle of the lid's edge goes when shut, as a share of the eye's radius,
# so the higher sides of the curved edge still cover the eye
UPPER_LID_SHUT_OVERSHOOT = 0.45


def create_upper_lid_mask(width: int, closed: float):
   """
   How much of each pixel the upper lid leaves showing, 1 is all of the eye and 0 is hidden behind the lid.
   A closed amount of 0 is the lid out of sight above the eye and 1 is the eye shut.
   """
   radius = width / 2
   lid_bottom = closed * (width + radius * UPPER_LID_SHUT_OVERSHOOT)
   half_width = radius * UPPER_LID_WIDTH_SCALE
   half_height = radius * UPPER_LID_HEIGHT_SCALE

   Y, X = np.ogrid[:width, :width]
   # Pixel centers, relative to the middle of the ellipse that makes the lid
   x = (X + 0.5 - radius) / half_width
   y = (Y + 0.5 - (lid_bottom - half_height)) / half_height
   # Roughly how many pixels inside the ellipse each pixel is, plenty accurate near the middle of its edge
   pixels_inside = (1.0 - np.sqrt(x ** 2 + y ** 2)) * half_height
   # Everything above the middle of the ellipse is lid too, so the eye never peeks out over its sides
   pixels_inside = np.where(y < 0, np.inf, pixels_inside)

   # Smoothed over a pixel so the edge does not look jagged as it sweeps
   return 1.0 - np.clip(pixels_inside + 0.5, 0.0, 1.0)


# Reflections of a light, which make the eye look wet and alive. Each is the middle of the reflection from the
# middle of the eye, its width and height, and how strong it is, all in pixels of a 160 pixel eye.
# The right eye is mirrored by the screen, so its reflections are mirrored too, which a real light would not do
CATCHLIGHTS = [
   ((-22, -24), (22, 18), 1.0),
   ((18, 20), (10, 10), 0.8),
]
CATCHLIGHT_COLOR = '#FFFFFF'
# How many pixels each catchlight's edge is softened over
CATCHLIGHT_SOFTNESS = 1.5


@functools.lru_cache(maxsize=4)
def get_catchlight_mask(width: int):
   """
   How much each pixel is covered by a catchlight, 0 is not at all and 1 is fully.
   Worked out once for each size since the catchlights never move.
   """
   scale = width / IRIS_PATTERN_DESIGN_WIDTH
   center = width / 2
   Y, X = np.ogrid[:width, :width]
   coverage = np.zeros((width, width))
   for (offset_x, offset_y), (light_width, light_height), strength in CATCHLIGHTS:
      half_width = light_width * scale / 2
      half_height = light_height * scale / 2
      x = (X + 0.5 - center - offset_x * scale) / half_width
      y = (Y + 0.5 - center - offset_y * scale) / half_height
      # Roughly how many pixels inside the oval each pixel is
      pixels_inside = (1.0 - np.sqrt(x ** 2 + y ** 2)) * min(half_width, half_height)
      light = np.clip(pixels_inside / CATCHLIGHT_SOFTNESS + 0.5, 0.0, 1.0) * strength
      coverage = np.maximum(coverage, light)
   coverage.setflags(write=False)
   return coverage


def draw_eye(base_img, rotation, iris_radius, pupil_radius, width=160, color='#4937A2', blink=0.0):
   """
   Blink is how far the upper lid is closed, 0 is open and 1 is shut.
   The lid hides only the eye, so the planets and orbits behind it carry on showing.
   """
   brightness, limbal, alpha = get_iris_pattern(width, pupil_radius)
   catchlights = get_catchlight_mask(width)

   palette = get_iris_palette(color)
   stops = [stop for stop, _ in palette]
   stop_colors = np.array([ImageColor.getrgb(stop_color)[:3] for _, stop_color in palette], dtype=float)
   eye_pixels = np.stack([np.interp(brightness, stops, stop_colors[:, channel]) for channel in range(3)], axis=-1)
   eye_pixels *= limbal[..., None]

   # The catchlights sit over the hollow pupil as well as the iris, so they make their own pixels solid
   catchlight_color = np.array(ImageColor.getrgb(CATCHLIGHT_COLOR), dtype=float)
   eye_pixels += (catchlight_color - eye_pixels) * catchlights[..., None]
   alpha = np.maximum(alpha, catchlights)

   if blink > 0:
      alpha = alpha * create_upper_lid_mask(width, blink)

   eye_img = Image.fromarray(np.round(eye_pixels).astype(np.uint8), mode='RGB')
   eye_img.putalpha(Image.fromarray(np.round(alpha * 255).astype(np.uint8), mode='L'))
   purple_box = get_centered_bounding_box((width, width))
   base_img.paste(eye_img, purple_box, eye_img)


def draw_planet_orbit(draw, ring_diameter: int, planet_angle: int, planet_size: int, planet_color: str):
   ring_box = get_centered_bounding_box((ring_diameter, ring_diameter))
   # Draw planet orbit ring
   # draw.ellipse(ring_box, outline='#251A39', width=1)

   planet_center = get_radial_point(planet_angle, ring_diameter / 2)
   debug(planet_center)
   planet_box = get_surrounding_bounding_box(planet_center, (planet_size, planet_size))
   debug('planet box', planet_box)
   draw.ellipse(planet_box, fill=planet_color)


def draw_rounded_arc(draw, diameter: int, width: int, start_angle: int, end_angle: int, color: str):
   loading_box = get_centered_bounding_box((diameter, diameter))
   debug('loading box', loading_box)
   draw.arc(loading_box, start_angle, end_angle, color, width)

   debug('ledge point', diameter / 2 - width / 2)
   arc_center_radius = round(diameter / 2 - width / 2)
   edge_circle_width = (width - 2, width - 2)

   start_edge_center = get_radial_point(start_angle, arc_center_radius)
   start_edge_box = get_surrounding_bounding_box(start_edge_center, edge_circle_width)
   debug('start_edge box', start_edge_box)
   draw.ellipse(start_edge_box, fill=color)

   end_edge_center = get_radial_point(end_angle, arc_center_radius)
   end_edge_box = get_surrounding_bounding_box(end_edge_center, edge_circle_width)
   debug('end_edge box', end_edge_box)
   draw.ellipse(end_edge_box, fill=color)

def draw_loader(draw, radius: int, width: int, segments: list[int], buffer: int, rotation_angle: int, trans_in: bool, trans_out: bool, trans_out_roller: float, erase_color='black'):
   """
   Erase color is what the parts of the loader rolling in or out are painted over with,
   see-through (0, 0, 0, 0) when drawing on a layer of its own.
   """
   arc_colors = ['#9C27B0', '#7B1FA2', '#4A148C']
   seg_start = rotation_angle

   for seg_index, seg_length in enumerate(segments):
      seg_end = seg_start - seg_length
      color = min(seg_index, len(arc_colors) - 1)
      draw_rounded_arc(draw, radius*2, width, seg_end, seg_start, arc_colors[color])
      seg_start = seg_end - buffer

   if trans_in:
      loading_box = get_centered_bounding_box((radius*2, radius*2))
      draw.pieslice(loading_box, rotation_angle + 10, 0, fill=erase_color)
   elif trans_out:
      loading_box = get_centered_bounding_box((radius*2, radius*2))
      draw.pieslice(loading_box, 0, round(trans_out_roller), fill=erase_color)


def draw_under_lid(base_img, draw_layer, blink: float, eye_width=160):
   """
   Draws something that sits on the eye, such as the loader, so the blink lid covers it along with the iris.
   draw_layer is given an ImageDraw for a see-through layer the size of the frame, and draws onto it.
   """
   layer = Image.new('RGBA', RESOLUTION, (0, 0, 0, 0))
   draw_layer(ImageDraw.Draw(layer))

   if blink > 0:
      # Only the eye's square has a lid, everything outside it is left showing
      showing = Image.new('L', RESOLUTION, 255)
      lid = create_upper_lid_mask(eye_width, blink)
      showing.paste(Image.fromarray(np.round(lid * 255).astype(np.uint8), mode='L'),
                    get_centered_bounding_box((eye_width, eye_width))[:2])
      alpha = np.asarray(layer.getchannel('A'), dtype=np.uint16) * np.asarray(showing, dtype=np.uint16) // 255
      layer.putalpha(Image.fromarray(alpha.astype(np.uint8), mode='L'))

   base_img.paste(layer, (0, 0), layer)

def new_frame():
   base_image = Image.new('RGB', RESOLUTION, 'black')
   draw = ImageDraw.Draw(base_image)
   return base_image, draw

def test_graphics():
   base_image, draw = new_frame()

   draw_eye(base_image, 35, 15, 37, 160)

   draw_planet_orbit(draw, 190, 210, 10, '#DA6849')
   draw_planet_orbit(draw, 230, 85, 5, '#0277BD')
   draw_planet_orbit(draw, 160, 8, 8, '#B71C1C')

   base_image.save('test_outputs/test_pillow.png')


if __name__ == "__main__":
   DEBUG_LOGGING = True
   test_graphics()
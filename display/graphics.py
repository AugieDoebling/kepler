from PIL import Image, ImageDraw, ImageOps
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

def draw_eye(base_img, rotation, iris_radius, width=160):
   eye_img = Image.linear_gradient('L').resize((width, width))
   eye_img = eye_img.rotate(rotation)
   eye_img = ImageOps.colorize(eye_img, black='#4937A2', white='#30224B')


   eye_mask = create_radial_alpha_mask(width, 37, iris_radius)
   purple_box = get_centered_bounding_box((width, width))

   eye_img.putalpha(eye_mask)
   base_img.paste(eye_img, purple_box, eye_img)


def draw_planet_orbit(draw, ring_diameter: int, planet_angle: int, planet_size: int, planet_color: str):
   ring_box = get_centered_bounding_box((ring_diameter, ring_diameter))
   draw.ellipse(ring_box, outline='#251A39', width=1)

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

def draw_loader(draw, radius: int, width: int, segments: list[int], buffer: int, rotation_angle: int, trans_in: bool, trans_out: bool, trans_out_roller: float):
   arc_colors = ['#9C27B0', '#7B1FA2', '#4A148C']
   seg_start = rotation_angle

   for seg_index, seg_length in enumerate(segments):
      seg_end = seg_start - seg_length
      color = min(seg_index, len(arc_colors) - 1)
      draw_rounded_arc(draw, radius*2, width, seg_end, seg_start, arc_colors[color])
      seg_start = seg_end - buffer

   if trans_in:
      loading_box = get_centered_bounding_box((radius*2, radius*2))
      draw.pieslice(loading_box, rotation_angle + 10, 0, fill='black')
   elif trans_out:
      loading_box = get_centered_bounding_box((radius*2, radius*2))
      draw.pieslice(loading_box, 0, round(trans_out_roller), fill='black')

def new_frame():
   base_image = Image.new('RGB', RESOLUTION, 'black')
   draw = ImageDraw.Draw(base_image)
   return base_image, draw

def test_graphics():
   base_image, draw = new_frame()

   draw_eye(base_image, 35, 15, 160)

   draw_planet_orbit(draw, 190, 210, 10, '#DA6849')
   draw_planet_orbit(draw, 230, 85, 5, '#0277BD')
   draw_planet_orbit(draw, 160, 8, 8, '#B71C1C')

   base_image.save('test_outputs/test_pillow.png')


if __name__ == "__main__":
   DEBUG_LOGGING = True
   test_graphics()
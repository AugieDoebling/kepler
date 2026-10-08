

def send_command(command):
   return

def set_debug_print(value: bool):
   """Whether the ESP32 echoes the commands it receives back over serial"""
   return {
      "T": 605,
      "cmd": 1 if value else 0,
   }

# MOTION COMMANDS

def go_to_initial_position():
   """Return to the default position"""
   return {
      "T": 100
   }

def move(forward_speed: int, left_speed: int, counterclockwise_rotation_speed: int):
   # TODO: speed validation assertions
   max_x = max_y = 0.07
   max_rot = 0.6

   return {
      "T": 1,
      "X": (forward_speed / 100) * max_x,
      "Y": (left_speed / 100) * max_y,
      "Yaw": (counterclockwise_rotation_speed / 100) * max_rot,
   }

def stop():
   return move(0, 0, 0)

def pose_angle_rotation(x_amp: int, y_amp: int, z_amp: int, frequency: int):
   # TODO: validation assertions
   max_amp = 0.3
   max_freq = 0.4

   return {
      "T": 3,
      "r": (x_amp / 100) * max_amp,
      "p": (y_amp / 100) * max_amp,
      "y": (z_amp / 100) * max_amp,
      "f": (frequency / 100) * max_freq,
   }

def set_self_balance(value: bool):
   return {
      "T": 4,
      "cmd": 1 if value else 0,
   }

def set_body_height(height: int):
   # TODO: validation assertions
   # these are defined in the docs as negative values, but using positive for now
   max_height = 140.83
   min_height = 60.83

   total_range = max_height - min_height
   percentage = height / 100;

   return {
      "T": 5,
      "cmd": (total_range * percentage) + min_height,
   }

def set_leg_position(leg: int, x: float, y: float, z: float):
   """
   :param leg: leg number. Value range: 0 ~ 5. Right front leg is number 0, right-side legs increase sequentially clockwise; left front leg is number 3, left-side legs increase sequentially counterclockwise.
   :param x: Specific positions for the x-axis, unit: mm.
   :param y:Specific positions for the y-axis, unit: mm.
   :param z:Specific positions for the z axis, unit: mm.
   """

   return {
      "T": 701,
      "leg": leg,
      "x": x,
      "y": y,
      "z": z,
   }

def set_leg_joint_angles(leg: int, coxa: float, femur: float, tibia: float, use_radians: bool = False):
   """

   :param leg: leg number. Value range: 0 ~ 5. Right front leg is number 0, right-side legs increase sequentially clockwise; left front leg is number 3, left-side legs increase sequentially counterclockwise.
   :param coxa: coxa is the hip joint rotation angle. Due to different leg mounting orientations on the hexapod robot, the initial angle and movable range differ for each hip joint. Specifically: Right front leg and left rear leg have an initial Coxa angle of -0.5235 rad, movable range -1.134 rad ~ 0 rad. Left front leg and right rear leg have an initial Coxa angle of 0.5235 rad, movable range 0 rad ~ 1.134 rad. Middle legs have an initial Coxa angle of 0 rad, movable range -0.7853 rad ~ 0.7853 rad.
   :param femur: femur is the thigh joint rotation angle. The initial angle is 0.5235 rad, movable range 0 rad ~ 1.57 rad. Increasing the angle rotates the joint downward, decreasing rotates upward.
   :param tibia: tibia is the shank joint rotation angle. The initial angle is 2.619 rad, movable range 0 rad ~ 3.1415 rad. Increasing the angle rotates the joint downward, decreasing rotates upward.
   :param use_radians: default is degrees
   """

   return {
      "T": 702 if use_radians else 703,
      "leg": leg,
      "coxa": coxa,
      "femur": femur,
      "tibia": tibia,
   }

# SAFETY COMMANDS

def emergency_stop():
   """
   Make every servo go limp at once. The ESP32 holds them limp for 10 seconds and then switches them
   back on by itself, and does nothing else in that time. The robot will drop onto its body.
   """
   return {
      "T": 0,
   }

def clear_emergency():
   """Clear the emergency stop flag that emergency_stop sets"""
   return {
      "T": 999,
   }

# LIGHT AND SCREEN COMMANDS

def set_led_brightness(io4_brightness: int, io5_brightness: int):
   """
   Set the brightness of the two light outputs on the ESP32 board.

   :param io4_brightness: Brightness of the light on pin IO4. Value range: 0 ~ 100, 0 is off.
   :param io5_brightness: Brightness of the light on pin IO5. Value range: 0 ~ 100, 0 is off.
   """
   # TODO: validation assertions
   max_brightness = 255

   return {
      "T": 132,
      "IO4": round((io4_brightness / 100) * max_brightness),
      "IO5": round((io5_brightness / 100) * max_brightness),
   }

# The screen is 128 pixels wide and the ESP32 draws its text 6 pixels to a character
OLED_LINE_CHARACTERS = 21

def write_oled_text(line: int, text: str, centered: bool = False):
   """
   Write one line of text on the small screen on the ESP32 board. The other lines keep what was last written to them.

   :param line: line number. Value range: 0 ~ 3. Line 0 is the top line.
   :param text: the text to show on that line.
   :param centered: put the text in the middle of the line, in place of starting at the left edge.
   """
   if centered:
      # The screen has no centering of its own, so the text is pushed across with spaces
      text = " " * max(0, (OLED_LINE_CHARACTERS - len(text)) // 2) + text

   return {
      "T": 13,
      "lineNum": line,
      "Text": text,
   }

def clear_oled_text():
   """Put the small screen back to its default display, in place of the text written with write_oled_text"""
   return {
      "T": -3,
   }

# WI-FI COMMANDS

def set_wifi_on_boot_mode(access_point_on: bool, connect_to_network: bool):
   mode = 0
   if access_point_on and connect_to_network:
      mode = 3
   elif connect_to_network:
      mode = 2
   elif access_point_on:
      mode = 1

   return {
      "T": 401,
      "cmd": mode,
   }

def set_access_point_network(ssid: str, password: str):
   return {
      "T": 402,
      "ssid": ssid,
      "password": password,
   }

def set_network_credentials(ssid: str, password: str):
   return {
      "T": 403,
      "ssid": ssid,
      "password": password,
   }

def set_duel_network_mode(ap_ssid: str, ap_password: str, sta_ssid: str, sta_password: str):
   return {
      "T": 404,
      "ap_ssid": ap_ssid,
      "ap_password": ap_password,
      "sta_ssid": sta_ssid,
      "sta_password": sta_password,
   }

def retrieve_wifi_config():
   return {"T":405}

def save_wifi_status_as_config():
   return {"T":406}

def new_wifi_config(access_point_on: bool, connect_to_network: bool, ap_ssid: str, ap_password: str, sta_ssid: str, sta_password: str):
   mode = 0
   if access_point_on and connect_to_network:
      mode = 3
   elif connect_to_network:
      mode = 2
   elif access_point_on:
      mode = 1

   return {
      "T": 407,
      "mode": mode,
      "ap_ssid": ap_ssid,
      "ap_password": ap_password,
      "sta_ssid": sta_ssid,
      "sta_password": sta_password,
   }

def turn_off_wifi():
   return {"T":408}

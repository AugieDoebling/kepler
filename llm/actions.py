from display.display_state import DisplayState
from head.head_state import HeadState
from head.pan_tilt import PAN_LIMITS, TILT_LIMITS
from hexarth.hexarth_state import HexarthState
from memory import memory_storage
from typing import Optional
from . import basic_tools, robot_status, weather, web_tools
from .timers import MAX_TIMER_MINUTES, Timers
from .llm_types import ActionSpec

SPIN_SPEED_LIMITS = (-100, 100)
SPIN_DURATION_LIMITS_MS = (2000, 10000)

# The sway amounts and tempo are a percentage of the most the robot can do
SWAY_LIMITS = (0, 100)
SWAY_DURATION_LIMITS_MS = (2000, 10000)

# Head speeds in degrees per second, from a slow turn to a brisk one
HEAD_SPEED_LIMITS = (10.0, 60.0)

def clamp(value: float, limits: tuple):
   return max(limits[0], min(limits[1], value))

class Actions:
   def __init__(self, display_state: DisplayState, hexarth_state: HexarthState, head_state: HeadState,
                timers: Optional[Timers] = None):
      self.display_state = display_state
      self.hexarth_state = hexarth_state
      self.head_state = head_state
      # Without somewhere to deliver a timer that goes off, there is no timer tool
      self.timers = timers

      specs = [
         ActionSpec(
            name="web_fetch",
            description="Fetches the content of a web page for the provided URL.",
            input_schema={
               "type": "object",
               "properties": {
                  "url": {"type": "string", "description": "The URL to fetch"},
               },
               "required": ["url"],
            },
            func=web_tools.web_fetch,
         ),
         ActionSpec(
            name="web_search",
            description="Performs a web search.",
            input_schema={
               "type": "object",
               "properties": {
                  "query": {"type": "string", "description": "The query to search for"},
                  "max_results": {"type": "integer", "description": "The maximum number of results to return (default: 3)"},
               },
               "required": ["query"],
            },
            func=web_tools.web_search,
         ),
         ActionSpec(
            name="get_weather",
            description="Get the current weather and the forecast for the next few days. Use this for any question about the weather instead of searching the web.",
            input_schema={
               "type": "object",
               "properties": {
                  "location": {"type": "string", "description": f"The town or city, optionally followed by a comma and the state or country, such as \"Portland, Oregon\". Leave it out for home, {weather.HOME_LOCATION}."},
                  "days": {"type": "integer", "description": f"How many days of forecast to get, counting today. Values between 1 and {weather.MAX_FORECAST_DAYS} (default: 3)."},
               },
               "required": [],
            },
            func=weather.get_weather,
         ),
         ActionSpec(
            name="get_time",
            description="Get the current date and time. Use this whenever the answer depends on today's date, the day of the week or the time.",
            input_schema={"type": "object", "properties": {}, "required": []},
            func=basic_tools.get_time,
         ),
         ActionSpec(
            name="calculate",
            description="Work out a maths expression exactly. Use this for any arithmetic, percentages, tips or unit conversions rather than doing it in your head.",
            input_schema={
               "type": "object",
               "properties": {
                  "expression": {"type": "string", "description": "The expression in Python syntax, such as \"18 * 0.2\" or \"sqrt(2) * 10\". Write powers as **. Functions: sqrt, sin, cos, tan, log, log10, exp, round, abs, min, max, floor, ceil. Constants: pi, e."},
               },
               "required": ["expression"],
            },
            func=basic_tools.calculate,
         ),
         ActionSpec(
            name="wikipedia_lookup",
            description="Look up a person, place, thing or event on Wikipedia and get the opening of its article. Better than a web search for facts and background.",
            input_schema={
               "type": "object",
               "properties": {
                  "topic": {"type": "string", "description": "What to look up, such as \"Mars\" or \"Golden Gate Bridge\"."},
               },
               "required": ["topic"],
            },
            func=basic_tools.wikipedia_lookup,
         ),
         ActionSpec(
            name="robot_status",
            description="Check on your own body: temperature, power supply, Wi-Fi, memory, storage and how long you have been awake. Use it when asked how you are feeling or whether anything is wrong with you.",
            input_schema={"type": "object", "properties": {}, "required": []},
            func=robot_status.robot_status,
         ),
         ActionSpec(
            name="move",
            description="Queue a movement command for the robot with specified speeds.",
            input_schema={
               "type": "object",
               "properties": {
                  "forward_speed": {
                     "type": "integer",
                     "description": "The forward movement speed. Values between -100 and 100. Negative values move the robot backwards.",
                  },
                  "left_speed": {
                     "type": "integer",
                     "description": "The lateral movement speed to the left. Values between -100 and 100. Negative values move the robot to the right.",
                  },
                  "travel_duration_ms": {
                     "type": "integer",
                     "description": "The duration of the movement in milliseconds. Values between 2000 and 10000",
                  },
               },
               "required": ["forward_speed", "left_speed", "travel_duration_ms"],
            },
            func=self.move,
         ),
         ActionSpec(
            name="spin",
            description="Turn the robot on the spot, without travelling anywhere. Use it to face a different way, to turn towards someone, or to twirl for fun.",
            input_schema={
               "type": "object",
               "properties": {
                  "rotation_speed": {
                     "type": "integer",
                     "description": "How fast to turn. Values between -100 and 100. Positive values turn counterclockwise, to the robot's left. Negative values turn clockwise, to the robot's right. At full speed a complete turn takes roughly ten seconds.",
                  },
                  "duration_ms": {
                     "type": "integer",
                     "description": "How long to turn for in milliseconds. Values between 2000 and 10000",
                  },
               },
               "required": ["rotation_speed", "duration_ms"],
            },
            func=self.spin,
         ),
         ActionSpec(
            name="dance",
            description="Dance by swaying the body in place, with the feet planted. Do this when feeling happy or excited: at good news, a compliment, a favourite subject, or when asked to dance. The robot must not be walking at the same time.",
            input_schema={
               "type": "object",
               "properties": {
                  "side_to_side": {
                     "type": "integer",
                     "description": "How far the body tips from side to side. Values between 0 and 100. 0 is none.",
                  },
                  "front_to_back": {
                     "type": "integer",
                     "description": "How far the body rocks forwards and backwards. Values between 0 and 100. 0 is none.",
                  },
                  "twist": {
                     "type": "integer",
                     "description": "How far the body twists left and right. Values between 0 and 100. 0 is none. A dance with any twist can only go half as fast.",
                  },
                  "tempo": {
                     "type": "integer",
                     "description": "How fast the body sways. Values between 0 and 100. 100 is one full sway every two and a half seconds. Faster for excited, slower for content.",
                  },
                  "duration_ms": {
                     "type": "integer",
                     "description": "How long to dance for in milliseconds. Values between 2000 and 10000",
                  },
               },
               "required": ["side_to_side", "front_to_back", "twist", "tempo", "duration_ms"],
            },
            func=self.dance,
         ),
         ActionSpec(
            name="move_head",
            description="Turn and tilt the robot's head to look in a direction. Both angles are absolute, not relative to where the head is now.",
            input_schema={
               "type": "object",
               "properties": {
                  "pan_degrees": {
                     "type": "number",
                     "description": f"The angle to turn the head to. Values between {PAN_LIMITS[0]:g} and {PAN_LIMITS[1]:g}. 0 is straight ahead, positive values look to the right, negative values look to the left.",
                  },
                  "tilt_degrees": {
                     "type": "number",
                     "description": f"The angle to tilt the head to. Values between {TILT_LIMITS[0]:g} and {TILT_LIMITS[1]:g}. The scale is inverted: 0 is looking flat and level, and negative values look up, so {TILT_LIMITS[0]:g} is looking as far up as the head goes. The head cannot look down below level.",
                  },
                  "speed": {
                     "type": "number",
                     "description": f"How fast the head moves, in degrees per second. Values between {HEAD_SPEED_LIMITS[0]:g} and {HEAD_SPEED_LIMITS[1]:g}. The speed reflects the robot's emotional mood: slow (10 to 20) for calm, sad, tired or thoughtful, medium (25 to 40) for relaxed and content, fast (45 to 60) for excited, startled, eager or alarmed.",
                  },
               },
               "required": ["pan_degrees", "tilt_degrees", "speed"],
            },
            func=self.move_head,
         ),
         ActionSpec(
            name="remember",
            description="Save a fact to long-term memory. Only use this when someone asks you to remember something. Everything else said in conversation is remembered on its own.",
            input_schema={
               "type": "object",
               "properties": {
                  "fact": {
                     "type": "string",
                     "description": "The fact as one sentence that makes sense on its own, naming who it is about rather than saying I, you or he. For example \"Sam's dentist appointment is on Friday at 3pm\".",
                  },
               },
               "required": ["fact"],
            },
            func=self.remember,
         ),
         ActionSpec(
            name="recall",
            description="Search long-term memory for what you know about a person, event or subject. Use it when someone asks whether you remember something, or when something from an earlier conversation would help you answer.",
            input_schema={
               "type": "object",
               "properties": {
                  "query": {
                     "type": "string",
                     "description": "What to look for, as a short question or a few words. For example \"when is Sam's dentist appointment\" or \"Augie's favourite food\".",
                  },
               },
               "required": ["query"],
            },
            func=self.recall,
         ),
         ActionSpec(
            name="forget",
            description="Delete something from long-term memory. Only use this when someone asks you to forget something, or says something you remember is wrong.",
            input_schema={
               "type": "object",
               "properties": {
                  "description": {"type": "string", "description": "What to forget, as a short description. For example \"Sam's dentist appointment\"."},
                  "memory_id": {"type": "integer", "description": "The number of the memory to forget. Only give this after forget has listed more than one match."},
               },
               "required": ["description"],
            },
            func=self.forget,
         ),
      ]
      if timers:
         specs.append(ActionSpec(
            name="timer",
            description="Set, list or cancel timers and reminders. When a timer goes off you will be told, so you can tell the user.",
            input_schema={
               "type": "object",
               "properties": {
                  "action": {"type": "string", "enum": ["set", "list", "cancel"], "description": "\"set\" to start a timer, \"list\" to see the ones running, or \"cancel\" to stop one."},
                  "reminder": {"type": "string", "description": "For \"set\", what the timer is for, such as \"take the pasta off the stove\"."},
                  "minutes": {"type": "number", "description": f"For \"set\", how many minutes from now it goes off, at most {MAX_TIMER_MINUTES}. Give this or at, not both."},
                  "at": {"type": "string", "description": "For \"set\", the clock time it goes off, such as \"15:30\" or \"3:30 PM\". Give this or minutes, not both."},
                  "timer_id": {"type": "integer", "description": "For \"cancel\", the number of the timer, from \"list\". Leave it out to cancel the only one running."},
               },
               "required": ["action"],
            },
            func=timers.timer,
         ))
      self.available_actions = {spec.name: spec for spec in specs}

   def get_actions(self):
      return list(self.available_actions.values())

   def call_action(self, name: str, arguments: dict):
      func = self.available_actions[name].func
      return func(**arguments)

   def move(self, forward_speed: int, left_speed: int, travel_duration_ms: int):
      """
      Queue a movement command for the robot with specified speeds.

      :param forward_speed: The forward movement speed. Values between -100 and 100. Negative values move the robot backwards.
      :param left_speed: The lateral movement speed to the left. Values between -100 and 100. Negative values move the robot to the right.
      :param travel_duration_ms: The duration of the movement in milliseconds. Values between 2000 and 10000
      """
      self.hexarth_state.queue_action("move", {"forward_speed": forward_speed, "left_speed": left_speed}, travel_duration_ms)

   def spin(self, rotation_speed: int, duration_ms: int):
      """
      Turn the robot on the spot, without travelling anywhere. Use it to face a different way, to turn towards someone, or to twirl for fun.

      :param rotation_speed: How fast to turn. Values between -100 and 100. Positive values turn counterclockwise, to the robot's left. Negative values turn clockwise, to the robot's right. At full speed a complete turn takes roughly ten seconds.
      :param duration_ms: How long to turn for in milliseconds. Values between 2000 and 10000
      """
      # The LLM does not always keep to the ranges it is given
      self.hexarth_state.queue_action(
         "move",
         {"forward_speed": 0, "left_speed": 0, "counterclockwise_rotation_speed": clamp(rotation_speed, SPIN_SPEED_LIMITS)},
         clamp(duration_ms, SPIN_DURATION_LIMITS_MS),
      )

   def dance(self, side_to_side: int, front_to_back: int, twist: int, tempo: int, duration_ms: int):
      """
      Dance by swaying the body in place, with the feet planted. Do this when feeling happy or excited: at good news, a compliment, a favourite subject, or when asked to dance. The robot must not be walking at the same time.

      :param side_to_side: How far the body tips from side to side. Values between 0 and 100. 0 is none.
      :param front_to_back: How far the body rocks forwards and backwards. Values between 0 and 100. 0 is none.
      :param twist: How far the body twists left and right. Values between 0 and 100. 0 is none. A dance with any twist can only go half as fast.
      :param tempo: How fast the body sways. Values between 0 and 100. 100 is one full sway every two and a half seconds. Faster for excited, slower for content.
      :param duration_ms: How long to dance for in milliseconds. Values between 2000 and 10000
      """
      # The LLM does not always keep to the ranges it is given
      self.hexarth_state.queue_action(
         "pose_angle_rotation",
         {
            "x_amp": clamp(side_to_side, SWAY_LIMITS),
            "y_amp": clamp(front_to_back, SWAY_LIMITS),
            "z_amp": clamp(twist, SWAY_LIMITS),
            "frequency": clamp(tempo, SWAY_LIMITS),
         },
         clamp(duration_ms, SWAY_DURATION_LIMITS_MS),
      )

   def move_head(self, pan_degrees: float, tilt_degrees: float, speed: float):
      """
      Turn and tilt the robot's head to look in a direction. Both angles are absolute, not relative to where the head is now.

      :param pan_degrees: The angle to turn the head to. Values between -60 and 60. 0 is straight ahead, positive values look to the right, negative values look to the left.
      :param tilt_degrees: The angle to tilt the head to. Values between -45 and 0. The scale is inverted: 0 is looking flat and level, and negative values look up, so -45 is looking as far up as the head goes. The head cannot look down below level.
      :param speed: How fast the head moves, in degrees per second. Values between 10 and 60. The speed reflects the robot's emotional mood: slow (10 to 20) for calm, sad, tired or thoughtful, medium (25 to 40) for relaxed and content, fast (45 to 60) for excited, startled, eager or alarmed.
      """
      # The LLM does not always keep to the ranges it is given
      self.head_state.queue_move(
         clamp(pan_degrees, PAN_LIMITS),
         clamp(tilt_degrees, TILT_LIMITS),
         clamp(speed, HEAD_SPEED_LIMITS),
      )

   def remember(self, fact: str):
      """
      Save a fact to long-term memory.

      :param fact: The fact as one sentence that makes sense on its own, naming who it is about.
      """
      memory_storage.store_memory(fact)
      return "Remembered."

   def recall(self, query: str):
      """
      Search long-term memory for what you know about a person, event or subject.

      :param query: What to look for, as a short question or a few words.
      """
      memories = memory_storage.recall(query)
      if not memories:
         return "Nothing remembered about that."
      return "\n".join(memories)

   def forget(self, description: str, memory_id: Optional[int] = None):
      """
      Delete something from long-term memory. Only use this when someone asks you to forget something, or says something you remember is wrong.

      :param description: What to forget, as a short description. For example "Sam's dentist appointment".
      :param memory_id: The number of the memory to forget. Only give this after forget has listed more than one match.
      """
      matches = memory_storage.recall_with_ids(description, mark_used=False)
      if memory_id is not None:
         # Only a memory that matches the description, so a made-up number can't delete something unrelated
         chosen = next((content for found_id, content in matches if found_id == int(memory_id)), None)
         if chosen is None:
            return f"Memory {memory_id} doesn't match {description!r}, nothing was forgotten."
         memory_storage.forget_memory(int(memory_id))
         return f"Forgotten: {chosen}"
      if not matches:
         return "Nothing remembered about that, so there is nothing to forget."
      if len(matches) == 1:
         found_id, content = matches[0]
         memory_storage.forget_memory(found_id)
         return f"Forgotten: {content}"
      listing = "\n".join(f"[{found_id}] {content}" for found_id, content in matches)
      return f"More than one memory matches. Call forget again with the memory_id of the one to forget, or ask which one is meant:\n{listing}"

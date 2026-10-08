import logging
import os
from display.display_state import DisplayState
from head.head_state import HeadState
from head.pan_tilt import PAN_LIMITS, TILT_LIMITS
from hexarth.hexarth_state import HexarthState
from ollama import Client
from .llm_types import ActionSpec

# Head speeds in degrees per second, from a slow turn to a brisk one
HEAD_SPEED_LIMITS = (10.0, 60.0)

def clamp(value: float, limits: tuple):
   return max(limits[0], min(limits[1], value))

class Actions:
   def __init__(self, display_state: DisplayState, hexarth_state: HexarthState, head_state: HeadState):
      self.display_state = display_state
      self.hexarth_state = hexarth_state
      self.head_state = head_state

      # The web tools run on Ollama's hosted service, which needs an API key even when the model runs locally
      ollama_api_key = os.environ.get("OLLAMA_API_KEY")
      if not ollama_api_key:
         logging.warning("OLLAMA_API_KEY is not set, web_search and web_fetch will fail. Add it to the .env file.")
      web_client = Client(headers={"Authorization": f"Bearer {ollama_api_key}"} if ollama_api_key else None)

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
            func=web_client.web_fetch,
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
            func=web_client.web_search,
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
      ]
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

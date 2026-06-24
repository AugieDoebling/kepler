from display.display_state import DisplayState
from hexarth.hexarth_state import HexarthState
from ollama import web_fetch, web_search

class Actions:
   def __init__(self, display_state: DisplayState, hexarth_state: HexarthState):
      self.display_state = display_state
      self.hexarth_state = hexarth_state

      self.available_actions = {
         "web_fetch": web_fetch,
         "web_search": web_search,
         "move": self.move,
      }
    
   def get_actions(self):
      return list(self.available_actions.values())

   def call_action(self, tool_call):
      func = self.available_actions[tool_call.function.name]
      return func(**tool_call.function.arguments)

   def move(self, forward_speed: int, left_speed: int, travel_duration_ms: int):
      """
      Queue a movement command for the robot with specified speeds.

      :param forward_speed: The forward movement speed. Values between -100 and 100. Negative values move the robot backwards.
      :param left_speed: The lateral movement speed to the left. Values between -100 and 100. Negative values move the robot to the right.
      :param travel_duration_ms: The duration of the movement in milliseconds. Values between 2000 and 10000
      """
      self.hexarth_state.queue_action("move", {"forward_speed": forward_speed, "left_speed": left_speed}, travel_duration_ms)
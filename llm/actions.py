import logging
import os
from display.display_state import DisplayState
from hexarth.hexarth_state import HexarthState
from ollama import Client
from .llm_types import ActionSpec

class Actions:
   def __init__(self, display_state: DisplayState, hexarth_state: HexarthState):
      self.display_state = display_state
      self.hexarth_state = hexarth_state

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

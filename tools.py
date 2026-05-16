from movement.move import TOOL_move
from typing import Any, Mapping
from output import log

all_tools = [
   TOOL_move,
]

tool_functions = {}
log("registering tools")
for tool in all_tools:
   name = tool['definition']['function']['name']
   log(name, end=", ")
   # log("registering", name)
   tool_functions[name] = tool['exec']
log('\nfinished registering tools')

def get_tool_definitions():
   return [tool['definition'] for tool in all_tools]

def handle_tool_call(tool_name: str, args: Mapping[str, Any]):
   log('calling', tool_name, args)
   if not tool_name in tool_functions:
      log("unknown tool: " + tool_name)

   return tool_functions[tool_name](args)
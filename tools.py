from movement.move import TOOL_move

all_tools = [
   TOOL_move,
]

tool_functions = {}
print("registering tools")
for tool in all_tools:
   name = tool['definition']['function']['name']
   print(name, end=", ")
   # print("registering", name)
   tool_functions[name] = tool['exec']
print('\nfinished registering tools')

def get_tool_definitions():
   return [tool['definition'] for tool in all_tools]

def handle_tool_call(tool_name: str, args: dict):
   print('calling', tool_name, args)
   if not tool_name in tool_functions:
      print("unknown tool: " + tool_name)

   return tool_functions[tool_name](args)
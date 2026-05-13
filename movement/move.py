import json

def move(direction, distance):
   print("moving", direction, distance)
   return json.dumps({"direction": direction, "distance": distance})

TOOL_move = {
   "definition": {
      "type": "function",
      "function": {
         "name": "move",
         "description": "Move around the room",
         "parameters": {
            "type": "object",
            "properties": {
               "direction": {
                  "type": "number",
                  "description": "direction of movement in degrees, 0 is straight forward"
               },
               "distance": {
                  "type": "number",
                  "description": "distance of movement to travel in millimeters"
               }
            },
            "required": ["direction", "distance"]
         }
      }
   },
   "exec": lambda args : move(args["direction"], args["distance"])
}
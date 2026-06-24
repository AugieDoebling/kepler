import logging
from hexarth import commands
from hexarth.hexarth_state import HexarthState
import time

class HexBot:
    def __init__(self, hexarth_state: HexarthState):
        self.hexarth_state = hexarth_state
        self.current_action = None
        self.current_action_start = time.perf_counter()
    
    def init_coms(self):
        pass
    
    def close_coms(self):
        pass

    def send_command(self, command: dict):
        logging.debug(f"Sending command: {command}")
        pass

    def update(self):
        if self.current_action is not None:
            time_since_action_start = time.perf_counter() - self.current_action_start
            if time_since_action_start > self.current_action["duration_ms"] / 1000:
                logging.info(f"Completing current command: {self.current_action['command']}")
                self.get_next_action()
        else:
            self.get_next_action()

        if self.current_action is None:
            logging.info("No actions enqueued.")
            return

        logging.info(f"New command {self.current_action['command']}")
        command = self.get_command(self.current_action["command"], self.current_action["args"])
        self.send_command(command)
            

    def get_next_action(self):
        logging.info("Getting next action")
        self.current_action = self.hexarth_state.pop_action()
        self.current_action_start = time.perf_counter()
    
    def get_command(self, command: str, args: dict) -> dict:
        if command == "go_to_initial_position":
            return commands.go_to_initial_position()
        elif command == "move":
            return commands.move(args["forward_speed"], args["left_speed"], args["counterclockwise_rotation_speed"])
        elif command == "stop":
            return commands.stop()
        elif command == "pose_angle_rotation":
            return commands.pose_angle_rotation(args["x_amp"], args["y_amp"], args["z_amp"], args["frequency"])
        elif command == "set_self_balance":
            return commands.set_self_balance(args["value"])
        elif command == "set_body_height":
            return commands.set_body_height(args["height"])
        elif command == "set_leg_position":
            return commands.set_leg_position(args["leg"], args["x"], args["y"], args["z"])
        elif command == "set_leg_joint_angles":
            return commands.set_leg_joint_angles(args["leg"], args["coxa"], args["femur"], args["tibia"])
        else:
            logging.error(f"Unknown command: {command}")
            return {}
    
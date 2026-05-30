from hexarth import commands
from hexarth_state import HexarthState
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
        pass

    def update(self):
        if self.current_action is not None:
            time_since_action_start = time.perf_counter() - self.current_action_start
            if time_since_action_start > self.current_action["duration_ms"] / 1000:
                self.get_next_action()
        else:
            self.get_next_action()

        if self.current_action is None:
            return

        command = self.get_command(self.current_action["command"], self.current_action["args"])
        self.send_command(command)
            

    def get_next_action(self):
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
        elif command == "set_wifi_on_boot_mode":
            return commands.set_wifi_on_boot_mode(args["access_point_on"], args["connect_to_network"])
        elif command == "set_access_point_network":
            return commands.set_access_point_network(args["ssid"], args["password"])
        elif command == "set_network_credentials":
            return commands.set_network_credentials(args["ssid"], args["password"])
        elif command == "set_duel_network_mode":
            return commands.set_duel_network_mode(args["ap_ssid"], args["ap_password"], args["sta_ssid"], args["sta_password"])
        elif command == "retrieve_wifi_config":
            return commands.retrieve_wifi_config()
        elif command == "save_wifi_status_as_config":
            return commands.save_wifi_status_as_config()
        elif command == "new_wifi_config":
            return commands.new_wifi_config(args["access_point_on"], args["connect_to_network"], args["ap_ssid"], args["ap_password"], args["sta_ssid"], args["sta_password"])
        elif command == "turn_off_wifi":
            return commands.turn_off_wifi()
        else:
            # TODO: log unknown command
            return {}
    
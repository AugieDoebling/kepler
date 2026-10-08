import json
import logging
from hexarth import commands
from hexarth.hexarth_state import HexarthState
import time

# The UART on GPIO14/15, wired to the ESP32 that drives the legs
SERIAL_PORT = "/dev/ttyAMA0"
SERIAL_BAUD = 115200
SERIAL_WRITE_TIMEOUT_SECONDS = 1.0

class HexBot:
    def __init__(self, hexarth_state: HexarthState, stationary_mode: bool = False):
        self.hexarth_state = hexarth_state
        self.stationary_mode = stationary_mode
        self.current_action = None
        self.current_action_start = time.perf_counter()
        self.serial = None
        if not stationary_mode:
            self.init_coms()

    def init_coms(self):
        # Imported here so that pyserial is only needed when the robot is really driven
        import serial

        logging.info("Opening serial port %s at %s baud", SERIAL_PORT, SERIAL_BAUD)
        self.serial = serial.Serial(SERIAL_PORT, SERIAL_BAUD, write_timeout=SERIAL_WRITE_TIMEOUT_SECONDS)
        # The ESP32 echoes every command back as text until it is told not to
        self.send_command(commands.set_debug_print(False))

    def close_coms(self):
        if self.serial:
            self.serial.close()
            self.serial = None

    def send_command(self, command: dict):
        if not command:
            # An unknown command. Sent as it is, the ESP32 would read the missing "T" as 0, the emergency stop
            return

        if self.stationary_mode:
            # Actions still run for their full duration, the command just never reaches the robot
            logging.info(f"Stationary mode, simulating command: {command}")
            return

        logging.debug(f"Sending command: {command}")
        # One JSON object per line is what the ESP32 reads
        self.serial.write((json.dumps(command) + "\n").encode())

    def update(self):
        if self.current_action is not None:
            time_since_action_start = time.perf_counter() - self.current_action_start
            if time_since_action_start > self.current_action["duration_ms"] / 1000:
                logging.info(f"Completing current command: {self.current_action['command']}")
                self.get_next_action()
                if self.current_action is None:
                    # Otherwise the robot carries on until the ESP32 has gone 3 seconds without a command
                    self.send_command(commands.stop())
        else:
            self.get_next_action()

        if self.current_action is None:
            return

        # Sent again on every update, the ESP32 stops by itself when it goes 3 seconds without a command
        command = self.get_command(self.current_action["command"], self.current_action["args"])
        self.send_command(command)
            

    def get_next_action(self):
        self.current_action = self.hexarth_state.pop_action()
        self.current_action_start = time.perf_counter()
        if self.current_action is not None:
            logging.info(f"Starting command {self.current_action['command']} {self.current_action['args']} "
                         f"for {self.current_action['duration_ms']}ms")
    
    def get_command(self, command: str, args: dict) -> dict:
        if command == "go_to_initial_position":
            return commands.go_to_initial_position()
        elif command == "move":
            return commands.move(args["forward_speed"], args["left_speed"], args.get("counterclockwise_rotation_speed", 0))
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
    
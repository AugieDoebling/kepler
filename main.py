import os
from datetime import datetime
from display import display_thread
from display.display_state import DisplayState, EyeState
from head import head_thread
from head.head_state import HeadState
from hardware import hardware_thread
from hexarth import hexarth_thread
from hexarth.hexarth_state import HexarthState
from input.input_state import start_input
import json
import logging
import platform
import signal
import subprocess
import sys
import threading
import time
from dotenv import load_dotenv
from llm import llm_thread
from llm.actions import Actions
from llm.llm_provider import create_provider
from llm.llm_state import LlmState
from memory import memory_thread
from output.output_state import start_output

def configure_logging():
    os.makedirs("logs", exist_ok=True)

    todays_date = datetime.today().strftime("%Y-%m-%d")
    logging.basicConfig(
        filename=F"logs/kepler_{todays_date}.log",
        filemode='a',
        level=logging.DEBUG,
        format="%(asctime)s [%(threadName)s] %(levelname)s: %(message)s"
    )

    # Errors also go to stderr so they are visible without opening the log file
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(logging.Formatter("%(asctime)s [%(threadName)s] %(levelname)s: %(message)s"))
    logging.getLogger().addHandler(stderr_handler)

    # Keep the LLM SDKs' request level debug output out of our log file
    for noisy_logger in ("anthropic", "google_genai", "httpx", "httpx2", "httpcore", "httpcore2"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

def log_uncaught_thread_exceptions():
    """
    Send the traceback of a thread that dies from an exception to the log file, not only to the terminal.
    """
    def log_thread_exception(args):
        thread_name = args.thread.name if args.thread else "unknown"
        logging.critical("Thread %s died from an uncaught exception", thread_name,
                         exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    threading.excepthook = log_thread_exception

def load_config():
    if not os.path.exists("kepler_config.json"):
        raise FileNotFoundError("kepler_config.json not found. Please create it.")
    
    with open("kepler_config.json", "r") as f:
        return json.load(f)

def log_startup_info():
    git_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()

    print("Git hash:", git_hash)
    logging.info("Git hash: " + git_hash)

    changed_files = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD', '--']).decode('ascii').splitlines()
    changed_summary = ", ".join(changed_files) if changed_files else "(none)"

    print("Changed files:", changed_summary)
    logging.info("Changed files: " + changed_summary)

    logging.info("Python %s on %s", sys.version.split()[0], platform.platform())

def log_config(config: dict):
    # The connection string holds a password
    shown = dict(config)
    if shown.get("database_connection_string"):
        shown["database_connection_string"] = "(set)"
    logging.info("Config: %s", json.dumps(shown))

def main():
    # First, so that a failure in anything after it reaches the log file
    configure_logging()
    log_uncaught_thread_exceptions()
    logging.info("Kepler starting")
    load_dotenv()
    config = load_config()

    log_startup_info()
    log_config(config)

    stationary_mode = config.get("stationary_mode", False)
    if stationary_mode:
        print("Stationary mode is on, movement commands will be simulated")

    display_state = DisplayState()
    hexarth_state = HexarthState()
    head_state = HeadState()
    actions = Actions(display_state, hexarth_state, head_state)
    llm_provider = create_provider(config)
    # Reading conversations for memories can use its own model, it uses the main one unless told otherwise
    memory_provider = create_provider({"llm": config["memory_llm"]}) if "memory_llm" in config else llm_provider
    output_state = start_output(config, display_state)
    input_state = start_input(config, output_state, display_state)
    llm_state = LlmState()

    # Only when there is no speech to set the pace
    paced_print = config.get("print_output_at_speech_speed", False) and output_state is None
    logging.info("Speech output %s, speech input %s, paced printing %s",
                 "on" if output_state else "off", "on" if input_state else "off", "on" if paced_print else "off")

    display_thread.start_thread(display_state, config)
    run_startup_checks(display_state, config)

    llm_thread.start_thread(actions, llm_state, llm_provider, output_state, input_state, paced_print,
                            display_state)
    hexarth_thread.start_thread(hexarth_state, stationary_mode)
    head_thread.start_thread(head_state, stationary_mode)
    hardware_thread.start_thread()
    memory_thread.start_thread(llm_state, memory_provider)
    logging.info("Startup finished, all threads started")

    wait_for_stop_request()
    shut_down()

def run_startup_checks(display_state: DisplayState, config: dict):
    startup_begin = time.perf_counter()

    # TODO: Add internet access check
    # TODO: Add hexbot comm check (if not in stationary)
    # TODO: Add head move check (if not in stationary, move all the way up, down, right and left, then return to center)

    # Wait at least five seconds, counting the time the checks took
    elapsed = time.perf_counter() - startup_begin
    logging.info(f"Startup completed in {elapsed:03.04f}." )
    time.sleep(max(0, 5 - elapsed))
    
    display_state.set_eye_state(EyeState.REGULAR)


def wait_for_stop_request():
    """
    Block until Ctrl-C, the terminal closing, or the process being asked to stop.
    """
    stop_requested = threading.Event()
    for stop_signal in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(stop_signal, lambda signal_number, frame: stop_requested.set())

    # Waits in short steps so the signal handlers get a chance to run
    while not stop_requested.wait(1):
        pass

def shut_down():
    print("\nShutting down")
    logging.info("Stop requested, shutting down")
    # The legs first, they are what could do harm if left going
    hexarth_thread.stop()
    head_thread.stop()
    # Saves what is left of the conversation, so it goes before anything that can wait less
    memory_thread.stop()
    display_thread.stop()
    logging.info("Kepler stopped")
    logging.shutdown()
    # The other threads run forever and would keep the process alive
    os._exit(0)



if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Goes to the log file with its traceback, and to stderr through the handler for errors
        logging.exception("Startup failed, shutting down")
        logging.shutdown()
        # The threads that were already started run forever and would keep the process alive
        os._exit(1)

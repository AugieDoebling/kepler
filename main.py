import os
from datetime import datetime
from display import display_thread
from display.display_state import DisplayState
from display.simulator import start_simulator
from hexarth import hexarth_thread
from hexarth.hexarth_state import HexarthState
from input.input_state import start_input
import json
import logging
import subprocess
from dotenv import load_dotenv
from llm import llm_thread
from llm.actions import Actions
from llm.llm_provider import create_provider
from llm.llm_state import LlmState
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

def main():
    # First, so that a failure in anything after it reaches the log file
    configure_logging()
    load_dotenv()
    config = load_config()

    log_startup_info()

    stationary_mode = config.get("stationary_mode", False)
    if stationary_mode:
        print("Stationary mode is on, movement commands will be simulated")

    display_state = DisplayState()
    hexarth_state = HexarthState()
    actions = Actions(display_state, hexarth_state)
    llm_provider = create_provider(config)
    output_state = start_output(config)
    input_state = start_input(config, output_state, display_state)
    llm_state = LlmState()

    # Only when there is no speech to set the pace
    paced_print = config.get("print_output_at_speech_speed", False) and output_state is None

    llm_thread.start_thread(actions, llm_state, llm_provider, output_state, input_state, paced_print,
                            display_state)
    display_thread.start_thread(display_state, start_simulator(config))
    hexarth_thread.start_thread(hexarth_state, stationary_mode)
    # TODO: Add memory thread



if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Goes to the log file with its traceback, and to stderr through the handler for errors
        logging.exception("Startup failed, shutting down")
        logging.shutdown()
        # The threads that were already started run forever and would keep the process alive
        os._exit(1)

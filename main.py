import os
from datetime import datetime
from display import display_thread
from display.display_state import DisplayState
from hexarth import hexarth_thread
from hexarth.hexarth_state import HexarthState
import json
import logging
import subprocess
from dotenv import load_dotenv
from llm import llm_thread
from llm.actions import Actions
from llm.llm_provider import create_provider
from llm.llm_state import LlmState
from llm.llm_types import Message

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
    load_dotenv()
    config = load_config()
    configure_logging()

    log_startup_info()

    stationary_mode = config.get("stationary_mode", False)
    if stationary_mode:
        print("Stationary mode is on, movement commands will be simulated")

    display_state = DisplayState()
    hexarth_state = HexarthState()
    actions = Actions(display_state, hexarth_state)
    llm_provider = create_provider(config)
    # TODO: Move system messages into config
    llm_state = LlmState([
        Message(role='system', content="You are a physical robot companion. You can talk to your human best friend and move "
                                 "around. Keep your responses to the length of a standard human conversation. Your "
                                 "personality is that of a whimsical English butler."),
        Message(role='system', content="All of your responses will be spoken aloud via text to speech, so only respond with "
                                 "text that should be spoken. No sound affects or context, and an absolute max length "
                                 "of 3 sentences, but most responses should be shorter."),
        Message(role='system', content="You've just booted up for the morning and are ready to start the day."),
        Message(role='system', content="Move around whenever you want, you're a robot so it makes sense to move around a bit"),
    ])
    
    llm_thread.start_thread(actions, llm_state, llm_provider)
    display_thread.start_thread(display_state)
    hexarth_thread.start_thread(hexarth_state, stationary_mode)
    # TODO: Add memory thread
    # TODO: Add talking thread



if __name__ == "__main__":
    main()



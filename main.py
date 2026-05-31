import os
from datetime import datetime
from display import display_thread
from display.display_state import DisplayState
from hexarth import hexarth_thread
from hexarth.hexarth_state import HexarthState
import json
import logging

def configure_logging():
    os.makedirs("logs", exist_ok=True)

    todays_date = datetime.today().strftime("%Y-%m-%d")
    logging.basicConfig(
        filename=F"logs/kepler_{todays_date}.log",
        filemode='a',
        level=logging.DEBUG,
        format="%(asctime)s [%(threadName)s] %(levelname)s: %(message)s"
    )

def load_config():
    if not os.path.exists("kepler_config.json"):
        raise FileNotFoundError("kepler_config.json not found. Please create it.")
    
    with open("kepler_config.json", "r") as f:
        return json.load(f)

def main():
    config = load_config()
    configure_logging()

    display_state = DisplayState()
    hexarth_state = HexarthState()
    
    # TODO: Add LLM thread
    display_thread.start_thread(display_state)
    hexarth_thread.start_thread(hexarth_state)
    # TODO: Add memory thread
    # TODO: Add talking thread



if __name__ == "__main__":
    main()



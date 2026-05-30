from display import display_thread
from display.display_state import DisplayState
from hexarth import hexarth_thread
from hexarth.hexarth_state import HexarthState


def main():
    display_state = DisplayState()
    hexarth_state = HexarthState()
    
    # TODO: Add LLM thread
    display_thread.start_thread(display_state)
    hexarth_thread.start_thread(hexarth_state)
    # TODO: Add memory thread
    # TODO: Add talking thread



if __name__ == "__main__":
    main()



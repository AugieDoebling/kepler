from display import display_thread
from display.display_state import DisplayState

def main():
    display_state = DisplayState()
    
    display_thread.start_thread(display_state)


if __name__ == "__main__":
    main()



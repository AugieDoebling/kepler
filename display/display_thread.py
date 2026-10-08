import logging
import time
import threading
from display.display_state import DisplayState
from display.planet_scenario import PlanetEyeScenario
from display.simulator import DisplaySimulator
from typing import Optional

FRAME_RATE = 30
FRAME_INTERVAL = 1.0 / FRAME_RATE

# A frame that takes this many times its share of a second is worth knowing about, but not on every frame
SLOW_FRAME_FACTOR = 3
SLOW_FRAME_LOG_INTERVAL_SECONDS = 10.0

def start_thread(display_state: DisplayState, simulator: Optional[DisplaySimulator] = None):
    """
    Create a thread that is responsible for displaying the planet eye.
    """
    display_thread = threading.Thread(target=loop, args=(display_state, simulator), name="display")
    display_thread.start()


def loop(display_state: DisplayState, simulator: Optional[DisplaySimulator] = None):
    logging.info("Starting display thread at %d frames a second, frames go to %s",
                 FRAME_RATE, type(simulator).__name__ if simulator else "nowhere")
    
    scenario = PlanetEyeScenario()
    last_frame_render_time = time.perf_counter()
    last_slow_frame_log_time = 0.0

    while True:
        frame_start_time = time.perf_counter()

        time_elapsed_since_last_update = frame_start_time - last_frame_render_time
        scenario.update(display_state, time_elapsed_since_last_update)

        frame_image = scenario.get_frame()
        if simulator:
            simulator.show(frame_image)
        else:
            # TODO: Send frame to display
            pass

        frame_generated_time = time.perf_counter()
        last_frame_render_time = frame_generated_time
        elapsed_time = frame_generated_time - frame_start_time
        if (elapsed_time > FRAME_INTERVAL * SLOW_FRAME_FACTOR
                and frame_generated_time - last_slow_frame_log_time > SLOW_FRAME_LOG_INTERVAL_SECONDS):
            logging.warning("Display frame took %.0fms, the target is %.0fms", elapsed_time * 1000, FRAME_INTERVAL * 1000)
            last_slow_frame_log_time = frame_generated_time
        sleep_time = max(0, FRAME_INTERVAL - elapsed_time)

        time.sleep(sleep_time)

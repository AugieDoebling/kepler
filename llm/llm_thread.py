import logging
import time
import threading
from .actions import Actions
from .llm_provider import LlmProvider
from .llm_state import LlmState
from .llm_types import LlmError
from display.display_state import DisplayState, EyeState
from input.input_state import InputState
from output.output_state import OutputState
from output.paced_print import print_at_speech_speed
from typing import Optional

# Stops a model that keeps calling tools from never handing the conversation back
MAX_TOOL_ROUNDS = 5

def start_thread(actions: Actions, llmState: LlmState, provider: LlmProvider,
                 output_state: Optional[OutputState] = None, input_state: Optional[InputState] = None,
                 paced_print: bool = False, display_state: Optional[DisplayState] = None):
    """
    Create a thread that is responsible for running the LLM.
    """
    llm_thread = threading.Thread(
        target=loop,
        args=(actions, llmState, provider, output_state, input_state, paced_print, display_state),
        name="llm")
    llm_thread.start()

def loop(actions: Actions, llmState: LlmState, provider: LlmProvider,
         output_state: Optional[OutputState] = None, input_state: Optional[InputState] = None,
         paced_print: bool = False, display_state: Optional[DisplayState] = None):
    logging.info("Starting LLM thread with provider %s", provider.name)

    tools = actions.get_actions()
    logging.info("Actions available to the LLM: %s", ", ".join(tool.name for tool in tools))
    tool_rounds = 0

    while True:
        awaiting_response, messages = llmState.get_status_and_messages()
        # Only the newest message, the ones before it were logged when they arrived
        logging.debug("Newest of %d messages: %s", len(messages), messages[-1] if messages else None)

        if not awaiting_response:
            time.sleep(1)
            continue

        # The display shows a loader while the robot is thinking
        if display_state:
            display_state.set_loading(True)
        logging.info("Sending %d messages to %s", len(messages), provider.name)
        request_start = time.perf_counter()
        try:
            response = provider.chat(messages, tools)
        except LlmError as e:
            logging.error("LLM request failed after %.1fs (%s): %s",
                          time.perf_counter() - request_start, type(e).__name__, e)
            # TODO: Call output state
            print("(I'm having trouble thinking right now.)")
            response = None
        finally:
            if display_state:
                display_state.set_loading(False)

        logging.debug("LLM response: %s", response)

        if response:
            logging.info("LLM replied in %.1fs with %d characters and %d tool calls",
                         time.perf_counter() - request_start, len(response.message.content),
                         len(response.message.tool_calls))
            if not response.message.content and not response.message.tool_calls:
                logging.warning("LLM reply was empty, nothing will be said or done")

            llmState.add_message(response.message, require_response=False)

            if response.message.content:
                if paced_print:
                    # Stands in for speech, so the reply takes about as long to appear as it would to say
                    if display_state:
                        display_state.set_eye_state(EyeState.SPEAKING)
                    try:
                        print_at_speech_speed(response.message.content)
                    finally:
                        if display_state:
                            display_state.set_eye_state(EyeState.REGULAR)
                else:
                    print(response.message.content)
                if output_state:
                    output_state.queue_output(response.message.content)

            if response.message.tool_calls:
                for tool_call in response.message.tool_calls:
                    print('tool call - ', tool_call.name, tool_call.arguments)
                    logging.info("Calling action %s with %s", tool_call.name, tool_call.arguments)
                    action_start = time.perf_counter()
                    try:
                        action_outcome = actions.call_action(tool_call.name, tool_call.arguments)
                    except Exception as e:
                        logging.exception("action %s failed with arguments %s", tool_call.name, tool_call.arguments)
                        action_outcome = f"Error: {e}"
                    logging.info("Action %s finished in %.1fs", tool_call.name, time.perf_counter() - action_start)
                    logging.debug('action outcome - %s', action_outcome)

                    # Every tool call needs a recorded result, hosted providers reject the history otherwise
                    result = "ok" if action_outcome is None else str(action_outcome)
                    llmState.add_tool_result(tool_call.id, tool_call.name, result, require_response=False)

                # The LLM's turn is not over until it responds without calling a tool
                tool_rounds += 1
                if tool_rounds < MAX_TOOL_ROUNDS:
                    llmState.set_awaiting_response(True)
                    continue
                logging.warning("LLM made %d tool calling rounds in a row, returning to the user", tool_rounds)

        tool_rounds = 0

        # With speech input on, the input state collects both spoken and typed messages
        logging.debug("Waiting for the user")
        user_response = input_state.wait_for_message() if input_state else input("--> ")
        logging.info("User said: %s", user_response)
        llmState.add_message_content("user", user_response, require_response=True)

import logging
import time
import threading
from .actions import Actions
from .llm_provider import LlmProvider
from .llm_state import LlmState
from .llm_types import LlmError
from display.display_state import DisplayState
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
        args=(actions, llmState, provider, output_state, input_state, paced_print, display_state))
    llm_thread.start()

def loop(actions: Actions, llmState: LlmState, provider: LlmProvider,
         output_state: Optional[OutputState] = None, input_state: Optional[InputState] = None,
         paced_print: bool = False, display_state: Optional[DisplayState] = None):
    logging.info("Starting LLM thread with provider %s", provider.name)

    tools = actions.get_actions()
    tool_rounds = 0

    while True:
        awaiting_response, messages = llmState.get_status_and_messages()
        logging.debug("current context - \n%s", messages)

        if not awaiting_response:
            time.sleep(1)
            continue

        # The display shows a loader while the robot is thinking
        if display_state:
            display_state.set_loading(True)
        try:
            response = provider.chat(messages, tools)
        except LlmError as e:
            logging.error("LLM request failed: %s", e)
            # TODO: Call output state
            print("(I'm having trouble thinking right now.)")
            response = None
        finally:
            if display_state:
                display_state.set_loading(False)

        logging.debug("LLM response: %s", response)

        if response:
            llmState.add_message(response.message, require_response=False)

            if response.message.content:
                if paced_print:
                    # Stands in for speech, so the reply takes about as long to appear as it would to say
                    if display_state:
                        display_state.set_speaking(True)
                    try:
                        print_at_speech_speed(response.message.content)
                    finally:
                        if display_state:
                            display_state.set_speaking(False)
                else:
                    print(response.message.content)
                if output_state:
                    output_state.queue_output(response.message.content)

            if response.message.tool_calls:
                for tool_call in response.message.tool_calls:
                    print('tool call - ', tool_call.name, tool_call.arguments)
                    try:
                        action_outcome = actions.call_action(tool_call.name, tool_call.arguments)
                    except Exception as e:
                        logging.exception("action %s failed", tool_call.name)
                        action_outcome = f"Error: {e}"
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
        user_response = input_state.wait_for_message() if input_state else input("--> ")
        llmState.add_message_content("user", user_response, require_response=True)

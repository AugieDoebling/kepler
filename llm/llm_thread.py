import logging
import time
import threading
from .actions import Actions
from .llm_provider import LlmProvider
from .llm_state import LlmState
from .llm_types import LlmError

def start_thread(actions: Actions, llmState: LlmState, provider: LlmProvider):
    """
    Create a thread that is responsible for running the LLM.
    """
    llm_thread = threading.Thread(target=loop, args=(actions, llmState, provider))
    llm_thread.start()

def loop(actions: Actions, llmState: LlmState, provider: LlmProvider):
    logging.info("Starting LLM thread with provider %s", provider.name)

    tools = actions.get_actions()

    while True:
        awaiting_response, messages = llmState.get_status_and_messages()
        logging.debug("current context - \n%s", messages)

        if not awaiting_response:
            time.sleep(1)
            continue

        try:
            response = provider.chat(messages, tools)
        except LlmError as e:
            logging.error("LLM request failed: %s", e)
            # TODO: Call output state
            print("(I'm having trouble thinking right now.)")
            response = None

        logging.debug("LLM response: %s", response)

        if response:
            llmState.add_message(response.message, require_response=False)

            if response.message.content:
                # TODO: Call output state
                print(response.message.content)

            if response.message.tool_calls:
                needed_tool_response = False
                for tool_call in response.message.tool_calls:
                    print('tool call - ', tool_call.name)
                    try:
                        action_outcome = actions.call_action(tool_call.name, tool_call.arguments)
                    except Exception as e:
                        logging.exception("action %s failed", tool_call.name)
                        action_outcome = f"Error: {e}"
                    logging.debug('action outcome - %s', action_outcome)

                    # Every tool call needs a recorded result, hosted providers reject the history otherwise
                    result = "ok" if action_outcome is None else str(action_outcome)
                    llmState.add_tool_result(tool_call.id, tool_call.name, result, require_response=False)

                    if action_outcome is not None:
                        needed_tool_response = True

                if needed_tool_response:
                    llmState.set_awaiting_response(True)
                    continue

        # TODO: Get message from input state
        user_response = input("--> ")
        llmState.add_message_content("user", user_response, require_response=True)

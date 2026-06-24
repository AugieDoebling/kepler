import logging
import time
import threading
from ollama import chat, ChatResponse
from .actions import Actions
from .llm_state import LlmState

def start_thread(actions: Actions, llmState: LlmState):
    """
    Create a thread that is responsible for running the LLM.
    """
    llm_thread = threading.Thread(target=loop, args=(actions, llmState))
    llm_thread.start()
    
def loop(actions: Actions, llmState: LlmState):
    logging.info("Starting LLM thread")

    tools = actions.get_actions()

    while True:
        awaiting_response, messages = llmState.get_status_and_messages()
        logging.debug("current context - \n%s", messages)
        
        if not awaiting_response:
            time.sleep(1)
            continue

        response: ChatResponse = chat(model='gemma4:e4b', messages=messages, tools=tools)

        logging.debug("LLM response: %s", response)


        llmState.add_message(response.message)

        if response.message.content:
            # TODO: Call output state
            print(response.message.content)

        if response.message.tool_calls:
            needed_tool_response = False
            for tool_call in response.message.tool_calls:
                print('tool call - ', tool_call.function.name)
                action_outcome = actions.call_action(tool_call)
                logging.debug('action outcome - %s', action_outcome)

                if action_outcome is not None:
                    llmState.add_message_content("tool", str(action_outcome), True)
                    needed_tool_response = True
            
            if needed_tool_response:
                continue
            


        # TODO: Get message from input state
        user_response = input("--> ")
        llmState.add_message_content("user", user_response, require_response=True)

        
        
        
       

    
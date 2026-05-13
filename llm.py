import tools
import ollama

background_content_messages = [
   {"role": "system", "content": "You are a physical robot companion. You can talk to your human best friend and move "
                                 "around. Keep your responses to the length of a standard human conversation. Your "
                                 "personality is whimsical and slightly annoyed."},
   {"role": "system", "content": "All of your responses will be spoken aloud via text to speech, so only respond with "
                                 "text that should be spoken. No sound affects or context, and an absolute max length "
                                 "of 3 sentences, but most responses should be shorter."},
   {"role": "system", "content": "You've just booted up for the morning and are ready to start the day."},
   {"role": "system", "context": "Move around whenever you want, you're a robot so it makes sense to move around a bit"},
]

class Llm:
   def __init__(self):
      self.messages = background_content_messages
      self.tool_definitions = tools.get_tool_definitions()

   def new_message(self, content: str, role: str ='user'):
      # TODO: Only maintain a given number of messages
      self.messages.append({
         'role': role,
         'content': content
      })

   def chat(self, current_message: str = ''):
      if current_message:
         self.new_message(current_message)

      print('messages', self.messages)

      chat_response = ollama.chat(
         model='gemma4:latest',
         messages=self.messages,
         tools=self.tool_definitions
      )

      # responses will either be a tool call or a conversational response.
      if chat_response.message.tool_calls:
         for call in chat_response.message.tool_calls:
            call_result = tools.handle_tool_call(call.function.name, call.function.arguments)
            self.new_message(call_result, "tool")

         # for tool calls, keep calling until you get a chat response
         return self.chat()

      else:
         self.new_message(chat_response.message.content, "agent")
         return chat_response.message
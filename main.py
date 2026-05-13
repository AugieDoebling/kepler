from llm import Llm


llm = Llm()
init_message = llm.chat()
print(init_message.content)

while True:
   new_message = input("---")
   response = llm.chat(new_message)
   print(response.content)


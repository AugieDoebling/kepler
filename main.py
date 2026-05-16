from llm import Llm
import asyncio
from aioconsole import ainput

async def main():
   llm = Llm()
   llm.chat()

   while True:
      new_message = await ainput("")
      llm.chat(new_message)

asyncio.run(main())

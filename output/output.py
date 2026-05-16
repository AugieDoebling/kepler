from config import config, OutputSetting
from colorama import Fore

def output(content: str):
   handlers = {
      OutputSetting.CONSOLE_DEBUG: console_output,
      OutputSetting.CONSOLE_CLEAN: console_output,
   }

   setting = config.output_setting
   handlers[setting](content)

def log(*args, **kwargs):
   handlers = {
      OutputSetting.CONSOLE_DEBUG: console_debug_log,
      OutputSetting.CONSOLE_CLEAN: lambda *a, **b: None,
   }

   setting = config.output_setting
   handlers[setting](*args, **kwargs)


# CONSOLE
def console_output(content: str):
   print(Fore.GREEN)
   print(content)
   print(Fore.RESET)

def console_debug_log(*args, **kwargs):
   print(*args, **kwargs)
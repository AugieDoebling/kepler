from enum import Enum

class OutputSetting(Enum):
   CONSOLE_DEBUG = 1
   CONSOLE_CLEAN = 2

class Config:
   def __init__(self):
      self.output_setting = OutputSetting.CONSOLE_CLEAN

config = Config()
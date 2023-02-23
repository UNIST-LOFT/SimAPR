import os
from typing import List, Tuple, Dict, Set
import asyncio
import telegram
from telegram.ext import Updater, CommandHandler, ContextTypes


class TelegramBot:
  def __init__(self, name, token, chat_id):
    self.core = telegram.Bot(token)
    self.updater = Updater(token)
    self.id = chat_id
    self.name = name

  def sendMessage(self, text):
    self.core.sendMessage(chat_id = self.id, text=text)

  def stop(self):
    self.updater.start_polling()
    self.updater.dispatcher.stop()
    self.updater.job_queue.stop()
    self.updater.stop()


class TestBot(TelegramBot):
  def __init__(self):
    self.token = "5410218005:AAETXOPfCT1mFASXV1ZYSXmrdUPyqOq_thQ"
    self.chat_id = "5603093896"
    super().__init__("TestBot", self.token, self.chat_id)
    self.updater.stop()

  def add_handler(self, cmd, func):
    self.updater.dispatcher.add_handler(CommandHandler(cmd, func))
  
  def start(self):
    self.sendMessage("Bot started")
    self.updater.start_polling()
    self.updater.idle()
  
  def proc_reply(self, update: telegram.Update, context: ContextTypes):
    self.sendMessage("Reply to {}".format(update.message.text))
  
  def add_default_handlers(self):
    self.add_handler("reply", self.proc_reply)

if __name__ == '__main__':
    text = "Hello world!"
    test_bot = TestBot()
    test_bot.add_default_handlers()
    test_bot.start()
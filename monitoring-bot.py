#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import glob
import os

import telegram.ext
from telegram.ext import Updater, CommandHandler

from datetime import datetime, time, tzinfo, timedelta

from PIL import Image

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

lastStatus = "not started"
unknownCount = 0
amberCount = 0

def lastFile():
    list_of_files = glob.glob('/monitoring/*.png') # * means all if need specific format then *.csv
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file

def parseImage(imageUrl):
    im = Image.open(imageUrl)
    pix = im.load()    
    width, height = im.size
    amber = 0
    red = 0
    grey = 0
    green = 0
    for (r, g, b) in im.getdata():
        if r > 128 and r < 138 and g > 114 and g < 124 and b > 71 and b < 81:
            amber += 1
        if r > 119 and r < 129 and g > 61 and g < 71 and b > 72 and b < 82:
            red += 1
        if r > 122 and r < 132 and g > 122 and g < 132 and b > 122 and b < 132:
            grey += 1
        if r > 63 and r < 73 and g > 110 and g < 120 and b > 94 and b < 104:
            green += 1            
    logger.info("Found {} amber dots".format(amber))
    logger.info("Found {} red dots".format(red))
    logger.info("Found {} grey dots".format(grey))
    logger.info("Found {} green dots".format(green))
    if red > 5000:
        return "red"
    elif grey > 5000:
        return "red"
    elif amber > 5000:
        return "amber"
    elif green > 5000:
        return "green"    
    else:
        return "unknown"

def callback_minute(context: telegram.ext.CallbackContext):
    global lastStatus
    global unknownCount
    global amberCount

    latestFile = lastFile()
    newStatus = parseImage(latestFile)

    if (lastStatus == "not started"):
        lastStatus = newStatus
        return

    if (lastStatus == newStatus):
        return
    elif (newStatus == "unknown"):
        unknownCount += 1
        amberCount = 0
        if (unknownCount <= 15):
            return
    elif (newStatus == "amber"):
        amberCount += 1
        unknownCount = 0
        if (amberCount <= 10):
            return
    else:
        unknownCount = 0
        amberCount = 0

    list_of_files = glob.glob('/monitoring/chats/*') 
    for file in list_of_files:
        chat_id = os.path.basename(file)
        logger.info("Sending status to {}".format(chat_id))
        try:
            context.bot.send_message(chat_id=chat_id, text="Status changed from {} to {}".format(lastStatus, newStatus))
            image = open(latestFile, 'rb')
            context.bot.send_photo(chat_id=chat_id, photo=image)
            image.close()
        except:
            logger.info("Cannot send message to chat id {}".format(chat_id))
    lastStatus = newStatus

def callback_weekend(context: telegram.ext.CallbackContext):
    latestFile = lastFile()
    newStatus = parseImage(latestFile)
    list_of_files = glob.glob('/monitoring/chats/*') 
    for file in list_of_files:
        chat_id = os.path.basename(file)
        logger.info("Sending status to {}".format(chat_id))
        try:
            context.bot.send_message(chat_id=chat_id, text="Current status is {}".format(newStatus))
            image = open(latestFile, 'rb')
            context.bot.send_photo(chat_id=chat_id, photo=image)
            image.close()
        except:
            logger.info("Cannot send message to chat id {}".format(chat_id))
    

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    update.message.reply_text('Hi! You have subscribed to alerts status notifications. Use /status to get current status of service; use /stop to unsubscribe')
    logger.info("Added {} chat".format(update.message.chat_id))
    f = open("/monitoring/chats/{}".format(update.message.chat_id), "a")
    f.write("{}".format(update.message.chat_id))
    f.close()
    status(update, context)

def stop(update, context):
    logger.info("Removed {} chat".format(update.message.chat_id))
    os.remove("/monitoring/chats/{}".format(update.message.chat_id))

def status(update, context):
    latestFile = lastFile()
    image = open(latestFile, 'rb')
    update.message.reply_photo(image)
    image.close()
    update.message.reply_text("Current status is {}".format(parseImage(latestFile)))

def alarm(context):
    """Send the alarm message."""
    job = context.job
    context.bot.send_message(job.context, text='Beep!')


def set_timer(update, context):
    """Add a job to the queue."""
    chat_id = update.message.chat_id
    try:
        # args[0] should contain the time for the timer in seconds
        due = int(context.args[0])
        if due < 0:
            update.message.reply_text('Sorry we can not go back to future!')
            return

        # Add job to queue and stop current one if there is a timer already
        if 'job' in context.chat_data:
            old_job = context.chat_data['job']
            old_job.schedule_removal()
        new_job = context.job_queue.run_once(alarm, due, context=chat_id)
        context.chat_data['job'] = new_job

        update.message.reply_text('Timer successfully set!')

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /set <seconds>')


def unset(update, context):
    """Remove the job if the user changed their mind."""
    if 'job' not in context.chat_data:
        update.message.reply_text('You have no active timer')
        return

    job = context.chat_data['job']
    job.schedule_removal()
    del context.chat_data['job']

    update.message.reply_text('Timer successfully unset!')


def main():
    """Run bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(os.environ['BOT_TOKEN'], use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", start))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("set", set_timer,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))
    dp.add_handler(CommandHandler("unset", unset, pass_chat_data=True))

    j = updater.job_queue
    job_minute = j.run_repeating(callback_minute, interval=60, first=0)
    # time is assumed in UTC here
    job_weekend = j.run_daily(callback_weekend, time(hour=17, minute=0), days=(5,6))
    # job_once = j.run_once(callback_weekend, 10)

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()

#!/usr/bin/python3
from aiogram import executor,asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from logging import handlers

import bot
import logging
import functions

if __name__ == '__main__':

    logging.basicConfig(format='%(asctime)s: %(name)s >> %(levelname)s >> (%(filename)s).%(funcName)s >> %(message)s',
                            filename=f'what_happens.log',
                            level=logging.INFO,
                            datefmt='%d/%m %H:%M:%S',
                            filemode='w')

    logging.handlers.RotatingFileHandler(filename=f'what_happens.log',maxBytes=5242880,backupCount=0,mode='w')
    
    # async scheduler используется для мониторинга времени напоминаний
    # каждую минуту вызывает send_notification
    # https://bit.ly/3ttSaBt
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(functions.send_notification, 'cron',minute='*')
    scheduler.add_job(functions.zeroing_count_taken, 'cron', hour='*')
    scheduler.add_job(functions.send_notification_allday, 'cron', hour='*')
    scheduler.start()

    executor.start_polling(bot.dp, 
    skip_updates=True,
    on_shutdown=functions.on_shutdown)

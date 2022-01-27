import shutil
import time
import bot

from datetime import datetime, timedelta
from keyboards import keyboard
from database import database_ as db
from aiogram import types, asyncio

def logs_backup():
    """Бэкап логов при завершение бота"""
    shutil.copy(f'what_happens.log', f'crash_logs_{time.strftime("%d_%m", time.localtime())}.log')

async def send_notification():
    """Рассылка уведомлений по времени"""

    # ВЫСЧИТЫВАЕМ ЛОКАЛЬНОЕ ВРЕМЯ ПОЛЬЗОВАТЕЛЯ ЧЕРЕЗ: UTC-0 +(-) ЧАСОВОЙ ПОЯС ПОЛЬЗОВАТЕЛЯ
    # ЕСЛИ ВЫСЧИТАННОЕ РАВНО ВРЕМЕНИ НАПОМИНАНИЯ - НАПОМИНАЕМ (НА УРОВНЕ БД НЕ УЧИТЫВАЮТСЯ ТАБЛЕТКИ С N/N ПРОПИТОГО В ДЕНЬ)

    for utc in range(-12,14):
        notification_list = await db.get_join_pills_data(utc, calc_notification_time(utc))
        if notification_list:
            users = dict() 
            for item in notification_list:

                text = f"Хэй-хэй, не забудь принять! 📣\n\n"

                try:
                    main_id = await db.get_main_message_id(item[0])
                    await bot.bot.delete_message(chat_id=item[0], message_id=main_id[0])
                except:
                    pass
                
                if not item[0] in users:
                    users[item[0]] = [(item[1], item[2], item[3])]
                else:
                    users[item[0]] += [(item[1], item[2], item[3])]

            for key, value in users.items():
                for item in value:
                    text += f"<a href='https://apteka.ru/search/?q={item[0]}'><b>{item[0]}</b></a>: oсталось <b>{item[2] - item[1]}</b> суточных приёмов 💊\n\n"
                
                shipped = await bot.bot.send_message(chat_id=key,text=text,reply_markup=keyboard.notification_keyboard,parse_mode='html',disable_web_page_preview=True)
                await db.set_main_message_id(message_id=shipped.message_id,user_id=key)

async def zeroing_count_taken():
    """Зануление выпитого в день по user localtime"""
    for utc in range(-12,14):
        if calc_notification_time(utc) == '00:00':
            await db.set_allcount_inday_to_null(utc=utc)

async def allday_send_message(header_text: str, utc: int):
    """Функция формирования сообщения, при allday напоминании"""
    allday_list = await db.get_allday_users(utc)
    if allday_list:
        for telegram_id in allday_list:
            user_pills = await db.get_notification_mypills(telegram_id[0])
            text = header_text
            for item in user_pills:
                text += f"<a href='https://apteka.ru/search/?q={item[1]}'><b>{item[1]}</b></a>: Осталось <b>{item[3] - item[2]}</b> дней курса и <b>{item[5] - item[4]}</b> суточных приёмов 💊\n\n"
            
            try:
                main_id = await db.get_main_message_id(telegram_id[0])
                await bot.bot.delete_message(chat_id=telegram_id[0], message_id=main_id[0])
            except:
                pass
                
            shipped = await bot.bot.send_message(chat_id=telegram_id[0],text=text,reply_markup=keyboard.notification_keyboard,parse_mode='html',disable_web_page_preview=True)
            await db.set_main_message_id(message_id=shipped.message_id, user_id=telegram_id[0])

async def send_notification_allday():
    """Проверка времени уведомления allday"""

    #ВЫСЫЛАЕМ НАПОМИНАНИЯ, КОГДА ЛОКАЛЬНОЕ ВРЕМЯ ЮЗЕРА РАВНО ОДНОМУ ИЗ, И КОГДА ALLDAY = 1

    for utc in range(-10,14):
        if calc_notification_time(utc) == '08:00':
            await allday_send_message('<b>Доброе утро!</b> ☀️\n', utc)
        elif calc_notification_time(utc) == '12:00':
            await allday_send_message('<b>Добрый день!</b> 🏞\n', utc)
        elif calc_notification_time(utc) == '18:00':
            await allday_send_message('<b>Добрый вечер!</b> 🌇\n', utc)

def utc_delta(message: types.Message):
    """Расчет UTC пользователя по времени из сообщения"""

    user_time = message.text.split(':') # Время сообщения от пользователя разбиваем на часы, минуты и секунды
    utc_time = datetime.utcnow() # вытаскиваем значение UTC из message
    
    if message.date.day < utc_time.day: 

        # если денб пользователя меньше чем день UTC, т.е. напр. 18.04 23:00 < 19.04 02:00
        # тогда делаем вот такую махинацию

        return -24 - (utc_time.hour - int(user_time[0]))
    elif int(user_time[0]) > utc_time.hour:

        return -(utc_time.hour - int(user_time[0]))
    elif int(user_time[0]) < utc_time.hour:

        return utc_time.hour - int(user_time[0])

def calc_notification_time(user_utc: int):
    """Функция выcчитывает время по UTC 0 из: время пользователя +(-) часовой пояс пользователя. Возвращает datetime.%H:%M"""

    if user_utc < 0:
        utc = time.strptime(f'{str(-user_utc)}', '%H')
        calculated = timedelta(hours=datetime.utcnow().hour, minutes=datetime.utcnow().minute) - timedelta(hours=utc.tm_hour)  
    else:
        utc = time.strptime(f'{str(user_utc)}', '%H')
        calculated = timedelta(hours=datetime.utcnow().hour, minutes=datetime.utcnow().minute) + timedelta(hours=utc.tm_hour)

    recalculated = timedelta(seconds=calculated.seconds) # потому что иногда calculated вовзращает: days, H:M:S. А нужно H:M:S
    return datetime.strptime(str(recalculated), '%H:%M:%S').strftime('%H:%M')

async def on_shutdown(dp):
    db.close_connection()
    logs_backup()

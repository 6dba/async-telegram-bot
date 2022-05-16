import time
import random
import re

from datetime import datetime, timedelta
from aiogram import Bot, types, asyncio
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.types.message import ContentType
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

import functions
from config import API_TOKEN
from dialogs import message as dialog
from database import database_ as db
from keyboards import keyboard
from states import DataState
from main import logging


# ОПРЕДЕЛЕНИЕ БОТА. ДИСПЕТЧЕРА

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())



# ОБРАБОТЧИКИ КОЛБЕКОВ 

@dp.callback_query_handler(lambda call: call.data == 'menu')
async def menu_button(callback_query: types.CallbackQuery):
    """Вывод главного меню, через callback"""
    await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,text=dialog.mainMenu,reply_markup=keyboard.MainMenu_keyboard)

    await bot.answer_callback_query(callback_query.id)
    logging.info(f'Callback Query ~ Catched by <{menu_button.__name__}> func ~ From {callback_query.from_user.id} : @{callback_query.from_user.username}')

@dp.callback_query_handler(lambda call: call.data == 'mypills')
async def get_mypills(callback_query: types.CallbackQuery):
    """Вывод всех таблеток"""
    pills_list = await db.get_mypills(callback_query.from_user.id)

    # ЕСЛИ ПОЛУЧЕННЫЙ СПИСОК ПУСТОЙ - РЕДАКТИРУЕМ СООБЩЕНИЕ МОЛ НИЧЕГО НЕТ + КНОПКА ГЛ МЕНЮ
    # ЕСЛИ ЕСТЬ - ВЫВОДИМ СПИСОК ПОКА ОН НЕ БОЛЬШЕ 6

    if not pills_list:
        await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,text=dialog.None_pills,reply_markup=keyboard.to_main_keyboard, parse_mode='html')
    else:
        text = "<b>Мои препараты</b>\n\n"
        for item in pills_list:

            text += f"<a href='https://apteka.ru/search/?q={item[1]}'><b>{item[1]}</b></a>:\nКурс длится <b>{item[2]}/{item[3]}</b> дней 🗓\nПринято в день: <b>{item[4]}/{item[5]}</b> 💊\n"

            if item[6] != 0:
                text += f"Дозировка: <b>{item[6]}</b> мг 💉\n"

            text += f"Время напоминания: <b>{item[7]}</b> ⏳\n"

            if item[8]: # если примечания не пустые, то выводим
                text += f"Примечание: <b>{item[8]}</b> 🗒\n"
            
            text += '\n'

        await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,text=text,reply_markup=keyboard.to_main_keyboard, parse_mode='html', disable_web_page_preview=True)
    await bot.answer_callback_query(callback_query.id)
    logging.info(f'Callback Query ~ Catched by <{get_mypills.__name__}> func ~ From {callback_query.from_user.id} : @{callback_query.from_user.username}')

@dp.callback_query_handler(lambda call: call.data == 'planconfirm')
async def confirm_plan(callback_query: types.CallbackQuery):
    """Выгрузка части данных о таблетка + возможность их подтверждения"""
    pills_list = await db.get_mypills(callback_query.from_user.id)

    # ЕСЛИ ПОЛУЧЕННЫЙ СПИСОК ПУСТОЙ - РЕДАКТИРУЕМ СООБЩЕНИЕ МОЛ НИЧЕГО НЕТ + КНОПКА ГЛ. МЕНЮ
    # ЕСЛИ ЕСТЬ - ВЫВОДИМ КОЛ-ВО КНОПОК = КОЛ-ВО ТАБЛЕТОК ЮЗЕРА И ОСНОВНЫЕ ДАННЫЕ О ТОМ, СКОЛЬКО В ДЕНЬ ОСТАЛОСЬ ВЫПИТЬ

    if not pills_list:
        await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,text=dialog.None_pills,reply_markup=keyboard.to_main_keyboard, parse_mode='html')
    else:
        text = "<b>Подтвердить приём</b>\n\n"
        keyboard.confirm_keyboard = InlineKeyboardMarkup(row_width=2)
        for item in pills_list:
            text += f"<a href='https://apteka.ru/search/?q={item[1]}'><b>{item[1]}</b></a>:\nКурс длится <b>{item[2]}/{item[3]}</b> дней 🗓\nПринято в день: <b>{item[4]}/{item[5]}</b> 💊\n"

            if item[6] != 0:
                text += f"Дозировка: <b>{item[6]}</b> мг 💉\n"

            text +='\n'

            keyboard.confirm_keyboard.insert(InlineKeyboardButton(f"{item[1]}",callback_data=f"confirm#{item[1]}"))
        keyboard.confirm_keyboard.add(InlineKeyboardButton('Главное меню 🏛', callback_data= 'menu'))

        await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,text=text,reply_markup=keyboard.confirm_keyboard, parse_mode='html',disable_web_page_preview=True)
    await bot.answer_callback_query(callback_query.id)
    logging.info(f'Callback Query ~ Catched by <{confirm_plan.__name__}> func ~ From {callback_query.from_user.id} : @{callback_query.from_user.username}')

@dp.callback_query_handler(lambda call: call.data.startswith('confirm#'))
async def confirm_button(callback_query: types.CallbackQuery):
    """Подтверждение выпитой таблетки"""

    # ДЕЛАЕМ СПЛИТ КОЛБЕКА И БЕРЕМ ПОСЛЕДНЮЮ ЕГО ЧАСТЬ - НАЗВАНИЕ ПРЕПАРАТА
    # ДАЛЕЕ ЗАПРОС В БД, БЕРЕМ ДАННЫЕ ПРЕПАРАТА И МЕНЯЕМ ЗНАЧЕНИЕ ВЫПИТОГО В ДЕНЬ

    pill_data = await db.get_concreteness_pilldata(callback_query.from_user.id, callback_query.data.split("#")[-1])

    taken_changed = pill_data[0][4] + 1

    if taken_changed == pill_data[0][5]: # если кол-во выпитого = кол-ву необходимого в день, то день курса ++ и кол-во выпитого ++ -> запись данных
        course_InDay_taken = pill_data[0][2] + 1
        
        if course_InDay_taken == pill_data[0][3]: # если кол-во пропитых дней курса == небходимому кол-ву дней, тогда удаляем напоминание
            await bot.answer_callback_query(callback_query.id, show_alert=True, text=f"{pill_data[0][1]}: поздравляем, вы завершили приём курса! {course_InDay_taken}/{pill_data[0][3]} дней! 🥳")
            await db.set_countInDay_taken(callback_query.from_user.id,callback_query.data.split("#")[-1], taken_changed)
            await db.set_course_taken(callback_query.from_user.id,callback_query.data.split("#")[-1], course_InDay_taken)
            await db.delete_user_drug(callback_query.from_user.id,callback_query.data.split("#")[-1])
            await confirm_plan(callback_query)
        else:
            await bot.answer_callback_query(callback_query.id, text=f"{pill_data[0][1]}: cуточная норма принята! ✅")
            await db.set_countInDay_taken(callback_query.from_user.id,callback_query.data.split("#")[-1], taken_changed)
            await db.set_course_taken(callback_query.from_user.id,callback_query.data.split("#")[-1], course_InDay_taken)
            await confirm_plan(callback_query)

    elif taken_changed < pill_data[0][5]:
        taken_changed = pill_data[0][4] + 1
        await bot.answer_callback_query(callback_query.id, text=f"{pill_data[0][1]}: приём подтвержден! 👌")
        await db.set_countInDay_taken(callback_query.from_user.id,callback_query.data.split("#")[-1], taken_changed)
        await confirm_plan(callback_query)

    else:
        await bot.answer_callback_query(callback_query.id, text="Хэй, не много ли будет? ⛔️")
    logging.info(f'Callback Query ~ Catched by <{confirm_button.__name__}> func ~ From {callback_query.from_user.id} : @{callback_query.from_user.username}')

@dp.callback_query_handler(lambda call: call.data == 'delplan')
async def delete_plan(callback_query: types.CallbackQuery):
    """Удаление данных о таблетках"""
    pills_list = await db.get_mypills(callback_query.from_user.id)

    # ЕСЛИ ПОЛУЧЕННЫЙ СПИСОК ПУСТОЙ - РЕДАКТИРУЕМ СООБЩЕНИЕ МОЛ НИЧЕГО НЕТ + КНОПКА ГЛ МЕНЮ
    # ЕСЛИ ЕСТЬ - ВЫВОДИМ КОЛ-ВО КНОПОК = КОЛ-ВО ТАБЛЕТОК ЮЗЕРА И ОСНОВНЫЕ ИХ ДАННЫЕ

    if not pills_list:
        await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,text=dialog.None_pills,reply_markup=keyboard.to_main_keyboard, parse_mode='html')
    else:
        text = "<b>Удалить напоминание</b>\n\n"
        keyboard.delete_keyboard = InlineKeyboardMarkup(row_width=2)
        for item in pills_list:
            pill = f"<a href='https://apteka.ru/search/?q={item[1]}'><b>{item[1]}</b></a>:\nКурс длится <b>{item[2]}/{item[3]}</b> дней 🗓\n\n"

            text += pill
            keyboard.delete_keyboard.insert(InlineKeyboardButton(f"{item[1]}",callback_data=f"delete#{item[1]}"))
        keyboard.delete_keyboard.add(InlineKeyboardButton('Главное меню 🏛', callback_data= 'menu'))

        await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id, text=text, reply_markup=keyboard.delete_keyboard, parse_mode='html', disable_web_page_preview=True)
    await bot.answer_callback_query(callback_query.id)
    logging.info(f'Callback Query ~ Catched by <{delete_plan.__name__}> func ~ From {callback_query.from_user.id} : @{callback_query.from_user.username}')

@dp.callback_query_handler(lambda call: call.data == ('edit'))
async def edit_plan(callback_query: types.CallbackQuery):
    """Меню изменения напоминаний"""

    if await db.get_user_allday(callback_query.from_user.id):
        await bot.edit_message_text(chat_id=callback_query.from_user.id,message_id=callback_query.message.message_id, text=dialog.edit, reply_markup=keyboard.edit_true_keyboard)
    else:
        await bot.edit_message_text(chat_id=callback_query.from_user.id,message_id=callback_query.message.message_id, text=dialog.edit, reply_markup=keyboard.edit_false_keyboard)
    
    await bot.answer_callback_query(callback_query.id)
    logging.info(f'Callback Query ~ Catched by <{edit_plan.__name__}> func ~ From {callback_query.from_user.id} : @{callback_query.from_user.username}')



# FSM ОБРАБОТЧИКИ КОЛБЕКОВ 

@dp.callback_query_handler(lambda call: call.data.startswith('note#'))
async def edit_note(callback_query: types.CallbackQuery, state: FSMContext):
    """Состояние редактирования заметок таблетки"""

    # СПЛИТ КОЛБЕКА И РАБОТАЕМ С НАЗВАНИЕМ ПРЕПАРАТА

    drug_name = callback_query.data.split("#")[-1]
    await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id, text="Напиши заметки для напоминаний 📝\nНапример: <u>пить после еды</u> 🍜", reply_markup=keyboard.to_main_keyboard, parse_mode='html')
    await state.update_data(message_id=callback_query.message.message_id,drug_name=drug_name)
    await DataState.edit_note.set()

    await bot.answer_callback_query(callback_query.id)
    logging.info(f'Callback Query ~ Catched by <{edit_note.__name__}> func ~ From {callback_query.from_user.id} : @{callback_query.from_user.username}')

@dp.callback_query_handler(lambda call: call.data.startswith('delete#') or call.data.startswith('yes#') or call.data.startswith('no'))
async def delete_button(callback_query: types.CallbackQuery):
    """Запрос на удаление + обработка подтверждения удаления"""

    # ЕСЛИ КОЛБЕК НАЧИНАЕТСЯ С DELETE, ТО РЕДАКТИРУЕМ СООБЩЕНИЯ, ТЕМ САМЫМ СПРАШИВАЮ ПОДТВЕРЖДЕНИЕ У ПОЛЬЗОВАТЕЛЯ, МОЛ, УДАЛИТЬ?
    # ЕСЛИ ПОЛЬЗОВАТЕЛЬ НАЖИНАЕМ НА КНОПКИ ПОДТВЕРЖДЕНИЯ, ТО ПРОИСХОДИТ ДЕЙСТВИЕ

    if callback_query.data.startswith('delete#'):
        yes_no = InlineKeyboardMarkup(row_width=2).insert(InlineKeyboardButton('Нет 🙅‍♀️',callback_data='no')).insert(InlineKeyboardButton('Да 👌', callback_data=f'yes#{callback_query.data.split("#")[-1]}'))
        
        await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id, 
        text=f'<b>{callback_query.data.split("#")[-1]}</b>: удалить напоминание? 🤔', 
        reply_markup=yes_no, parse_mode='html')

    elif callback_query.data.startswith('yes#'):
        await db.delete_user_drug(callback_query.from_user.id, callback_query.data.split("#")[-1])
        await bot.answer_callback_query(callback_query.id, text=f'{callback_query.data.split("#")[-1]}: напоминание удалено! ✅')
        await menu_button(callback_query)
    else:
        await delete_plan(callback_query)
    
    await bot.answer_callback_query(callback_query.id)
    logging.info(f'Callback Query ~ Catched by <{delete_button.__name__}> func ~ From {callback_query.from_user.id} : @{callback_query.from_user.username}')

@dp.callback_query_handler(lambda call: call.data == 'addplan')
async def add_plan(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало процесса добавления препарата"""
    
    # ВЫВОД НАЧАЛЬНЫХ СООБЩЕНИЙ + УСТАНОВКА СОСТОЯНИЯ ДОБАВЛЕНИЯ

    drugs_count = await db.count_user_drugs(callback_query.from_user.id) # Берем кол-во напоминаний пользователя -> возваращает список кортежей -> берем нужное число

    if drugs_count[0][0] < 6:
        await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,text=dialog.start_addplan)
        time.sleep(1.5)
        await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,text=dialog.drug_name_addplan, reply_markup=keyboard.to_main_keyboard)
        
        await state.update_data(message_id=callback_query.message.message_id)
        await DataState.wait_drug_name.set()
    else:
        await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,text=dialog.pills_limit, reply_markup=keyboard.to_main_keyboard)
    await bot.answer_callback_query(callback_query.id)
    logging.info(f'Callback Query ~ Catched by <{add_plan.__name__}> func ~ From {callback_query.from_user.id} : @{callback_query.from_user.username}')

@dp.callback_query_handler(lambda call: call.data.startswith('time#'))
async def edit_time(callback_query: types.CallbackQuery, state: FSMContext):
    """Перенаправление на состояния редактирования времени"""

    # БЕРЕМ НАЗВАНИЕ ПРЕПАРАТА, И ID СООБЩЕНИЯ С КОТОРОГО НАЧАЛОСЬ РЕДАКТИРОВАНИЕ - СУЕМ В КЭШ
    # ДАЛЕЕ УСТАНАВЛИВАЕМ СОСТОЯНИЯ ИЗМЕНЕНИЯ ВРЕМЕНИ - СРАБОТАЕТ ФУНКЦИЯ стр.622 - <course_time_written>

    drug_name = callback_query.data.split("#")[-1]
    await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id, text="Когда тебе напомнить? ⏳", reply_markup=keyboard.to_main_keyboard)
    await state.update_data(message_id=callback_query.message.message_id,drug_name=drug_name)
    await DataState.edit_time.set()

    await bot.answer_callback_query(callback_query.id)
    logging.info(f'Callback Query ~ Catched by <{edit_time.__name__}> func ~ From {callback_query.from_user.id} : @{callback_query.from_user.username}')

@dp.callback_query_handler(lambda call: call.data.startswith('edit#'))
async def edit_button(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик колбеков из меню редактирования"""

    # ПЕРВОЕ - ИЗМЕНЕНИЕ ПАРАМЕТРА ALLDAY, ЕСЛИ ЕСТЬ НУЖНЫЙ НАМ КОЛБЕК И БАЗА ДАННЫХ ВОЗВРАЩАЕТ ПАРАМЕТР ALLDAY ЮЗЕРА TRUE - МЕНЯЕМ НА FALSE
    # ВЫЗЫВАЕМ МЕНЮ EDIT СНОВА, ГДЕ МЕНЯЕТСЯ ВИД КНОПКИ

    data = callback_query.data.split("#")[-1]
    if data == 'allday' and await db.get_user_allday(callback_query.from_user.id):
        await db.set_allday(callback_query.from_user.id, False)
        await edit_plan(callback_query)
    elif data == 'allday':
        await db.set_allday(callback_query.from_user.id, True)
        await bot.answer_callback_query(callback_query_id=callback_query.id,show_alert=True, text=dialog.allday_message)
        await edit_plan(callback_query)

    # ВТОРОЕ - РЕДАКТИРОВАНИЕ ВРЕМЕНИ НАПОМИНАНИЯ ПРЕПАРАТА

    if data == 'time':
        pills_list = await db.get_mypills(callback_query.from_user.id)

        if not pills_list:
            await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,text=dialog.None_pills,reply_markup=keyboard.to_main_keyboard, parse_mode='html')
        else:
            text = "<b>Редактировать время</b><\n\n"
            keyboard.confirm_keyboard = InlineKeyboardMarkup(row_width=2)
            for item in pills_list:
                pill = f"<a href='https://apteka.ru/search/?q={item[1]}'><b>{item[1]}</b></a>:\nКурс длится <b>{item[2]}/{item[3]}</b> дней 🗓\nВремя напоминания: <b>{item[7]}</b> ⏳\n\n"

                text += pill
                keyboard.confirm_keyboard.insert(InlineKeyboardButton(f"{item[1]}",callback_data=f"time#{item[1]}"))
            keyboard.confirm_keyboard.add(InlineKeyboardButton('Назад', callback_data= 'edit'))

            await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,text=text,reply_markup=keyboard.confirm_keyboard, parse_mode='html',disable_web_page_preview=True)
    
    # ТРЕТЬЕ - РЕДАКТИРОВАНИЕ ПРИМЕЧАНИЙ ПРЕПАРАТА

    if data == 'note':
        pills_list = await db.get_mypills(callback_query.from_user.id)

        if not pills_list:
            await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,text=dialog.None_pills,reply_markup=keyboard.to_main_keyboard, parse_mode='html')
        else:
            text = "<b>Редактировать примечание</b>\n\n"
            keyboard.confirm_keyboard = InlineKeyboardMarkup(row_width=2)
            for item in pills_list:
                
                if item[8]: # если примечания не пустые, то выводим
                    text += f"<a href='https://apteka.ru/search/?q={item[1]}'><b>{item[1]}</b></a>:\nПримечание: <b>{item[8]}</b> 🗒\n\n"

                keyboard.confirm_keyboard.insert(InlineKeyboardButton(f"{item[1]}",callback_data=f"note#{item[1]}"))
            keyboard.confirm_keyboard.add(InlineKeyboardButton('Назад', callback_data= 'edit'))

            await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,text=text,reply_markup=keyboard.confirm_keyboard, parse_mode='html',disable_web_page_preview=True)
    
    if data == 'UTC':
      await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,text="Какое время у тебя сейчас? 🙃\n" + f"Например, у меня: <b>{time.strftime('%H:%M',time.localtime())}</b> 🕙" , 
      reply_markup=keyboard.to_edit_keyboard, parse_mode='html')
      await state.update_data(message_id=callback_query.message.message_id)
      await DataState.edit_utc.set()
      
    await bot.answer_callback_query(callback_query.id)
    logging.info(f'Callback Query ~ Catched by <{edit_time.__name__}> func ~ From {callback_query.from_user.id} : @{callback_query.from_user.username}')



# ОБРАБОТЧИКИ КОМАНД

@dp.message_handler(commands=['start'], state = '*')
async def start_handler(message: types.Message, state: FSMContext):
    """Обработка команды start. Вывод текста и меню"""

    # ВСЕ НАЧИНАЕТСЯ С КОМАНДЫ СТАРТ, ПРИ НАЖАТИИ ПРОВЕРКА НА НАЛИЧИЕ ПОЛЬЗОВАТЕЛЯ В БД
    # ПРИ ОТСУТСТВИЕ ПОЛЬЗОВАТЕЛЯ - ДОБАВЛЯЕМ

    if not await db.exist_user(user_id=message.from_user.id):
        await db.insert_new_user(user_id=message.from_user.id)
    await bot.send_message(message.chat.id,dialog.start_html.format(first_name=message.from_user.first_name),parse_mode='html',reply_markup=keyboard.replMenu_keyboard)
    await menu_handler(message, state)
    logging.info(f'Message Handler ~ Catched by <{start_handler.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')

@dp.message_handler(commands=['help'], state = '*')
async def help_handler(message: types.Message, state: FSMContext):
    """Обработка команды help. Вывод текста и меню"""
    await bot.send_message(chat_id=message.chat.id,text=dialog.help,parse_mode='html')
    await state.finish()
    logging.info(f'Message Handler ~ Catched by <{help_handler.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')

@dp.message_handler(lambda message: message.text == "Главное меню 🏛", state = '*')
@dp.message_handler(commands=['menu'], state = '*')
async def menu_handler(message: types.Message,state: FSMContext):
    """Главное меню"""

    # ДАБЫ НЕ ПЛОДИТЬ КУЧУ 'ГЛАВНЫХ МЕНЮ' - ПРИДУМАНА СИЕ КОНСТРУКЦИЯ, ПОПЫТКА УДАЛЕНИЕ СТАРОГО СООБЩЕНИЯ ГЛАВНОГО МЕНЮ
    # ID КОТОРОГО ХРАНИТЬСЯ В БД, ПРИ НЕУДАЧЕ - ПРОДОЛЖАЕМ РАБОТУ И ПРОСТО ЗАСЫЛАЕМ НОВОЕ ГЛАВНОЕ МЕНЮ -> ЗАПИСЫВАЕМ ЕГО ID В БД

    if await state.get_state() == 'DataState:menu_exec':
        if message.text == "Главное меню 🏛" or message.text == "/menu":
            await bot.delete_message(message.from_user.id,message.message_id)
        return

    else:
        await DataState.menu_exec.set()
        try:
            main_id = await db.get_main_message_id(message.from_user.id)
            await bot.delete_message(chat_id=message.from_user.id, message_id=main_id[0])
        except:
            pass

        if message.text == "Главное меню 🏛" or message.text == "/menu":
            await bot.delete_message(message.from_user.id,message.message_id)
        
        shipped = await bot.send_message(message.from_user.id,dialog.mainMenu,reply_markup=keyboard.MainMenu_keyboard)
        await db.set_main_message_id(message_id=shipped.message_id, user_id=message.from_user.id)
        await state.finish()
        logging.info(f'Message Handler ~ Catched by <{menu_handler.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')



# FSM ОБРАБОТЧИКИ addplan

# обработчики команд во время состояния добавления
@dp.callback_query_handler(lambda call: call.data == 'exit' or call.data == 'add',state = DataState.wait_choose)
async def callback_choose(callback_query: types.CallbackQuery, state: FSMContext):
    """Разветвление при добавлении заметок"""
    
    # ПОЛЬЗОВАТЕЛЮ БЫЛ ПРЕДЛОЖЕНО - ДОБАВИТЬ ЗАМЕТКИ ИЛИ НЕТ
    # ДА - УСТАНАВЛИВАЕМ СЛЕДУЮЩУЮ СТАДИЮ
    # НЕТ - СОХРАНЯЕМ

    addplan_id_message = await state.get_data('message_id')

    if callback_query.data == 'add':
        await bot.answer_callback_query(callback_query.id)
        await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=addplan_id_message['message_id'],text="Напиши заметки для напоминаний 📝\nНапример: <u>пить после еды</u> 🍜" 
            ,reply_markup=keyboard.to_main_keyboard, parse_mode='html')
        await DataState.next()
        
    elif callback_query.data == 'exit':
        user_data = await state.get_data()
        await db.insert_new_data(user_id=callback_query.from_user.id,
                                drug_name=user_data['drug_name'],
                                course_taking=user_data['course_taking'],
                                course_taken=user_data['course_taken'],
                                count_day=user_data['course_inday'],
                                dose=user_data['dose'],
                                time=user_data['time'],
                                note='')
        await bot.edit_message_text(chat_id=callback_query.from_user.id,message_id=addplan_id_message['message_id'], text="<b>Напоминание добавлено!</b> 🎉",parse_mode='html')
        time.sleep(1.5)
        await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.mainMenu, reply_markup=keyboard.MainMenu_keyboard)
        await state.finish()
    logging.info(f'FSM Callback Query ~ Catched by <{callback_choose.__name__}> func ~ From {callback_query.from_user.id} : @{callback_query.from_user.username}')

@dp.callback_query_handler(lambda call: call.data == 'menu' or call.data == 'edit', state='*')
async def callback_fsm_menu_edit(callback_query: types.CallbackQuery, state: FSMContext):
    """Вывод главного меню, через callback"""

    # ОБНУЛЕНИЕ СОСТОНИЯ, ВЫВОД ГЛАВНОГО МЕНЮ / НАСТРОЕК
    await state.finish()

    if callback_query.data == 'menu':
      await menu_button(callback_query)
    if callback_query.data == 'edit':
      await edit_plan(callback_query)
  
    logging.info(f'FSM Callback Query ~ Catched by <{callback_fsm_menu_edit.__name__}> func ~ From {callback_fsm_menu_edit.from_user.id} : @{callback_fsm_menu_edit.from_user.username}')

async def utc_exist(user_id: int, state: FSMContext):
    addplan_id_message = await state.get_data('message_id')

    utc_exist = await db.get_user_utc(user_id)
    if not utc_exist:
        await bot.edit_message_text(chat_id=user_id, message_id=addplan_id_message['message_id'],text="Какое время у тебя сейчас? 🙃\n" + f"Например, у меня: <b>{time.strftime('%H:%M',time.localtime())}</b> 🕙" 
        , reply_markup=keyboard.to_main_keyboard, parse_mode='html')
        await DataState.next() # <user_utc_written>
    else:
        await bot.edit_message_text(chat_id=user_id, message_id=addplan_id_message['message_id'],text="Укажи время, когда тебе лучше напоминать.. ⏳" 
            , reply_markup=keyboard.to_main_keyboard)
        await DataState.wait_time.set()

@dp.callback_query_handler(lambda call: call.data == 'skip', state= DataState.wait_dose)
async def skip_dose(callback_query: types.CallbackQuery, state: FSMContext):
    """Пропуск дозировки"""
    
    await bot.answer_callback_query(callback_query.id)
    await state.update_data(dose=0)
    await utc_exist(callback_query.from_user.id,state)
    logging.info(f'FSM Message Handler ~ Catched by <{skip_dose.__name__}> func ~ From {callback_query.from_user.id} : @{callback_query.from_user.username}')

# обработчики состояния добавления 
@dp.message_handler(state = DataState.wait_drug_name)
async def drug_name_written(message: types.Message, state: FSMContext):
    """Обработка ввода препарата"""

    addplan_id_message = await state.get_data('message_id') # id сообщения из которого вызвалось меню добавления - для последующего редактирования сообщения
    
    # НЕМНОГО КОСТЫЛЬНАЯ ЛОГИКА, НО ПО ДРУГОМУ СООБЩЕНИЯ НЕ ОТРЕДАКТИРУЕШЬ
    # ЕСЛИ ВВОД НЕПРАВИЛЬНЫЙ -> РЕДАКТИРУЕТСЯ СООБЩЕНИЕ И ОЖИДАНИЕ ПОВТОРНОГО ВВОДА, ЧТОБЫ НЕ БЫЛО ИСКЛЮЧЕНИЙ ИЗ-ЗА ТОГО, ЧТО СООБЩЕНИЕ ОДИНАКОВОЕ, К СООБЩЕНИЮ ДОБАВЛЯЕТСЯ РАНДОМНЫЙ СМАЙЛИК :)

    if message.text.isdigit() or not set(".,:;!?_*+=<>()/@$'#^¤%&){}\"\\").isdisjoint(message.text) or len(message.text) > 60: # если строка не только буквы или в строке превышена допустимая длина
        await bot.delete_message(message.from_user.id, message.message_id)
        try:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_error + random.choice(dialog.SMILE),reply_markup=keyboard.to_main_keyboard)
        except:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_error + random.choice(dialog.SMILE),reply_markup=keyboard.to_main_keyboard)
            logging.exception(f'FSM Message Handler Edit ~ Catched by <{drug_name_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')
        return

    elif await db.exist_drug(message.from_user.id, message.text):
      await bot.delete_message(message.from_user.id, message.message_id)
      try:
          await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.drug_exist + random.choice(dialog.SMILE), reply_markup=keyboard.to_main_keyboard)
      except:
          await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.drug_exist + random.choice(dialog.SMILE), reply_markup=keyboard.to_main_keyboard)
          logging.exception(f'FSM Message Handler Edit ~ Catched by <{drug_name_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')
      return

    # ЕСЛИ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ - ВВЕДЕНЫЙ ПРЕПАРАТ ЗАНОСИТСЯ В КЭШ

    await state.update_data(drug_name=message.text)
    await bot.delete_message(message.from_user.id, message.message_id)
    await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text="Теперь напиши, сколько дней длится полный курс? 🗓",reply_markup=keyboard.to_main_keyboard)
    # Для последовательных шагов можно не указывать название состояния, обходясь next()
    await DataState.next()
    logging.info(f'FSM Message Handler ~ Catched by <{drug_name_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')

@dp.message_handler(state = DataState.wait_course_taking)
async def course_taking_written(message: types.Message, state: FSMContext):
    """Обработка ввода дней курса препарата"""
    
    addplan_id_message = await state.get_data('message_id')

    if not message.text.isdigit():
        await bot.delete_message(message.from_user.id, message.message_id)
        try:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_error + random.choice(dialog.SMILE),reply_markup=keyboard.to_main_keyboard)
        except:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_error + random.choice(dialog.SMILE),reply_markup=keyboard.to_main_keyboard)
            logging.exception(f'FSM Message Handler Edit ~ Catched by <{course_taking_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')
        return

    elif int(message.text) == 0 or int(message.text) > 365:        
        await bot.delete_message(message.from_user.id, message.message_id)
        try:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_unreal + random.choice(dialog.SMILE), reply_markup=keyboard.to_main_keyboard)
        except:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_unreal + random.choice(dialog.SMILE), reply_markup=keyboard.to_main_keyboard)
            logging.exception(f'FSM Message Handler Edit ~ Catched by <{course_taking_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')
        return

    await state.update_data(course_taking=int(message.text))
    await bot.delete_message(message.from_user.id, message.message_id)
    await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text="Сколько дней курса уже прошло? 📆",reply_markup=keyboard.to_main_keyboard)
   
    await DataState.next()
    logging.info(f'FSM Message Handler ~ Catched by <{course_taking_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')

@dp.message_handler(state = DataState.wait_course_taken)
async def course_taken_written(message: types.Message, state: FSMContext):
    """Обработка ввода уже прошедних дней курса препарата"""
    
    addplan_id_message = await state.get_data('message_id')
    course_taking = await state.get_data('course_taking')

    if not message.text.isdigit():
        await bot.delete_message(message.from_user.id, message.message_id)

        try:
           await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_error + random.choice(dialog.SMILE),reply_markup=keyboard.to_main_keyboard)
        except:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_error + random.choice(dialog.SMILE),reply_markup=keyboard.to_main_keyboard)
            logging.exception(f'FSM Message Handler Edit ~ Catched by <{course_taken_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')
        return

    elif int(message.text) >= int(course_taking['course_taking']):
        await bot.delete_message(message.from_user.id, message.message_id)
        
        try:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_more_than_need + random.choice(dialog.SMILE), reply_markup=keyboard.to_main_keyboard)
        except:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_more_than_need + random.choice(dialog.SMILE), reply_markup=keyboard.to_main_keyboard)
            logging.exception(f'FSM Message Handler Edit ~ Catched by <{course_taken_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')
        return

    await state.update_data(course_taken=int(message.text))
    await bot.delete_message(message.from_user.id, message.message_id)
    await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text="Сколько таблеток нужно пить в день? 💊",reply_markup=keyboard.to_main_keyboard)
   
    await DataState.next()
    logging.info(f'FSM Message Handler ~ Catched by <{course_taken_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')

@dp.message_handler(state = DataState.wait_inday)
async def course_inday_written(message: types.Message, state: FSMContext):
    """Обработка ввода необходимого кол-ва таблеток в день"""
    
    addplan_id_message = await state.get_data('message_id')

    if not message.text.isdigit():
        await bot.delete_message(message.from_user.id, message.message_id)
        try:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_error + random.choice(dialog.SMILE),reply_markup=keyboard.to_main_keyboard)
        except:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_error + random.choice(dialog.SMILE),reply_markup=keyboard.to_main_keyboard)
            logging.exception(f'FSM Message Handler Edit ~ Catched by <{course_inday_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')
        return
    elif int(message.text) == 0 or int(message.text) > 30:  
        await bot.delete_message(message.from_user.id, message.message_id)
        try:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_unreal + random.choice(dialog.SMILE), reply_markup=keyboard.to_main_keyboard)
        except:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_unreal + random.choice(dialog.SMILE), reply_markup=keyboard.to_main_keyboard)
            logging.exception(f'FSM Message Handler Edit ~ Catched by <{course_inday_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')        
        return

    await state.update_data(course_inday=int(message.text))
    await bot.delete_message(message.from_user.id, message.message_id)
    await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text="Напиши дозировку препарата в мг 💉",reply_markup=keyboard.skip_dose)
   
    await DataState.next()
    logging.info(f'FSM Message Handler ~ Catched by <{course_inday_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')

@dp.message_handler(state = DataState.wait_dose)
async def course_dose_written(message: types.Message, state: FSMContext):
  """Обработка ввода дозировки"""
    
  addplan_id_message = await state.get_data('message_id')

  try:
    float(message.text)
  except:
      await bot.delete_message(message.from_user.id, message.message_id)
      try:
          await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_error_dose + random.choice(dialog.SMILE), reply_markup=keyboard.skip_dose,parse_mode='html')
      except:
          await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_error_dose + random.choice(dialog.SMILE), reply_markup=keyboard.skip_dose,parse_mode='html')
          logging.exception(f'FSM Message Handler Edit ~ Catched by <{course_dose_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')        
      return
  await bot.delete_message(message.from_user.id, message.message_id)
  await state.update_data(dose=float(message.text))

  # ЕСЛИ У ПОЛЬЗОВАТЕЛЯ ЕЩЕ НЕ ЗАДАН ЧАСОВОЙ ПОЯС - ПЕРЕВОДИМ СОСТОНИЯ НА ВВОД ЛОКАЛЬНОГО ВРЕМЕНИ

  await utc_exist(message.from_user.id, state)
  logging.info(f'FSM Message Handler ~ Catched by <{course_dose_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')

@dp.message_handler(state = DataState.edit_utc)
@dp.message_handler(state = DataState.wait_utc)
async def user_utc_written(message: types.Message, state: FSMContext):
    """Обработка ввода времени, для определения часового пояса"""
    
    addplan_id_message = await state.get_data('message_id')

    if re.search(r'^(([0,1][0-9])|(2[0-3])):[0-5][0-9]$', message.text):
        await bot.delete_message(message.from_user.id, message.message_id)
        await db.set_utc(message.from_user.id,functions.utc_delta(message))
    else:
        await bot.delete_message(message.from_user.id, message.message_id)
        try:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_error_time + random.choice(dialog.SMILE),reply_markup=keyboard.to_main_keyboard,parse_mode='html')
        except:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_error_time + random.choice(dialog.SMILE),reply_markup=keyboard.to_main_keyboard,parse_mode='html')
            logging.exception(f'FSM Message Handler Edit ~ Catched by <{user_utc_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')

        return
  
    if await state.get_state() == 'DataState:edit_utc':
      await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'], text="<b>Часовой пояс обновлен!</b> 🎉", parse_mode='html')
      time.sleep(1.5)
      
      if await db.get_user_allday(message.from_user.id):
        await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'], text=dialog.edit, reply_markup=keyboard.edit_true_keyboard)
      else:
        await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'], text=dialog.edit, reply_markup=keyboard.edit_false_keyboard)
      
      await state.finish()
      logging.info(f'FSM Message Handler ~ Catched by <{user_utc_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')
      
      return

    await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text="Укажи время, когда тебе напомнить.. ⏳" 
      ,reply_markup=keyboard.to_main_keyboard)

    await DataState.next()
    logging.info(f'FSM Message Handler ~ Catched by <{user_utc_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')

@dp.message_handler(state = DataState.edit_time)
@dp.message_handler(state = DataState.wait_time)
async def course_time_written(message: types.Message, state: FSMContext):
    """Обработка ввода времени напоминания"""
    
    addplan_id_message = await state.get_data('message_id')

    if re.search(r'^(([0,1][0-9])|(2[0-3])):[0-5][0-9]$', message.text):
        await bot.delete_message(message.from_user.id, message.message_id)
        await state.update_data(time=message.text)
    else:
        await bot.delete_message(message.from_user.id, message.message_id)
        try:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_error_time + random.choice(dialog.SMILE),reply_markup=keyboard.to_main_keyboard,parse_mode='html')
        except:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_error_time + random.choice(dialog.SMILE),reply_markup=keyboard.to_main_keyboard,parse_mode='html')
            logging.exception(f'FSM Message Handler Edit ~ Catched by <{course_time_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')
        return

    ### РАЗВИЛКА ПРИ РАЗЛИЧНЫХ СОСТОЯНИЯХ: РЕДАКТИРОВАНИE ВРЕМЕНИ ИЛИ ОЖИДАНИE ВРЕМЕНИ ПРИ ДОБАВЛЕНИИ НОВОГО ПРЕПАРАТА

    if await state.get_state() == 'DataState:wait_time':

        await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text="По желанию можешь добавить примечания 🗒" 
            , reply_markup=keyboard.exit_or_add_keyboard)
        await DataState.next()

    elif await state.get_state() == 'DataState:edit_time':

        edit_time = await state.get_data()
        await db.set_time(user_id=message.from_user.id,hh_mm=edit_time['time'],drug_name=edit_time['drug_name'])

        await bot.edit_message_text(chat_id=message.from_user.id,message_id=addplan_id_message['message_id'], text="<b>Время напоминания обновлено!</b> 🎉", parse_mode='html')
        time.sleep(1.5)
        await bot.edit_message_text(chat_id=message.from_user.id,message_id=addplan_id_message['message_id'],text=dialog.mainMenu, reply_markup=keyboard.MainMenu_keyboard)
        await state.finish()
    logging.info(f'FSM Message Handler ~ Catched by <{course_time_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')

@dp.message_handler(state = DataState.edit_note)
@dp.message_handler(state = DataState.wait_note)
async def course_note_written(message: types.Message, state: FSMContext):
    """Обработка ввода заметок"""
    
    addplan_id_message = await state.get_data('message_id')
    await state.update_data(note=message.text)
    user_data = await state.get_data()

    if len(message.text) > 70:
        await bot.delete_message(message.from_user.id, message.message_id)
        try:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_error + random.choice(dialog.SMILE),reply_markup=keyboard.to_main_keyboard)
        except:
            await bot.edit_message_text(chat_id=message.from_user.id, message_id=addplan_id_message['message_id'],text=dialog.input_error + random.choice(dialog.SMILE),reply_markup=keyboard.to_main_keyboard)
            logging.exception(f'FSM Message Handler Edit ~ Catched by <{drug_name_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')
        return

    # РАЗВИЛКА, ЕСЛИ СОСТОЯНИЕ ДОБАВЛЕНИЕ - БЕРЕМ ВСЕ ВНЕСЕННЫЕ ДАННЫЕ ИЗ КЭША И СОХРАНЯЕМ КАК НОВОЕ НАПОМИНАНИЕ
    # ЕСЛИ СОСТОЯНИЕ РЕДАКТИРОВАНИЯ - ОБНОВЛЯЕМ ПРИМЕЧАНИЯ У НАПОМИНАНИЯ
    # СБРАСЫВАЕМ СОСТОЯНИЕ И КЭШ

    if await state.get_state() == 'DataState:wait_note':

        await db.insert_new_data(user_id=message.from_user.id,
                            drug_name=user_data['drug_name'],
                            course_taking=user_data['course_taking'],
                            course_taken=user_data['course_taken'],
                            count_day=user_data['course_inday'],
                            dose=user_data['dose'],
                            time=user_data['time'],
                            note=user_data['note'])
        await bot.delete_message(message.from_user.id,message.message_id)
        await bot.edit_message_text(chat_id=message.from_user.id,message_id=addplan_id_message['message_id'], text="<b>Напоминание добавлено!</b> 🎉",parse_mode='html')

    elif await state.get_state() == 'DataState:edit_note':

        edit_note = await state.get_data()
        await db.set_note(user_id=message.from_user.id, drug_name=edit_note['drug_name'],note=edit_note['note'])
        await bot.delete_message(message.from_user.id,message.message_id)
        await bot.edit_message_text(chat_id=message.from_user.id,message_id=addplan_id_message['message_id'], text="<b>Примечание обновлено!</b> 🎉",parse_mode='html')

    time.sleep(1.5)
    await bot.edit_message_text(chat_id=message.from_user.id,message_id=addplan_id_message['message_id'],text=dialog.mainMenu, reply_markup=keyboard.MainMenu_keyboard)
    await state.finish()
    logging.info(f'FSM Message Handler ~ Catched by <{course_note_written.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')



# ОБРАБОТЧИКИ КОНТЕНТА
@dp.message_handler(content_types=['sticker'])
async def sticker_message(message: types.Message):
    """Удаляет стикеры, дабы не было спама"""
    await bot.delete_message(message.from_user.id, message.message_id)
    logging.info(f'Content Message Handler ~ Catched by <{sticker_message.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')

@dp.message_handler(content_types=['sticker'], state = '*')
async def sticker_message_fsm(message: types.Message):
    """Удаляет стикеры, дабы не было спама. При состоянии."""
    await bot.delete_message(message.from_user.id, message.message_id)
    logging.info(f'FSM Content Message Handler ~ Catched by <{sticker_message_fsm.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')

@dp.message_handler(content_types=['text'])
async def echo_message(message: types.Message):
    """Удаляет текст, дабы не было спама"""
    await bot.delete_message(message.from_user.id, message.message_id)
    logging.info(f'Content Message Handler ~ Catched by <{echo_message.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')

@dp.message_handler(content_types=ContentType.ANY)
async def unknown_message(message: types.Message):
    """Ответ на любой присланный контент, кроме 'text'"""
    await message.reply(dialog.idontknow, parse_mode='html')
    logging.info(f'FSM Content Message Handler ~ Catched by <{unknown_message.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')

@dp.message_handler(content_types=ContentType.ANY, state = '*')
async def unknown_message_fsm(message: types.Message):
    """Ответ на любой присланный контент, кроме 'text'. При состоянии."""
    await bot.delete_message(message.from_user.id, message.message_id)
    logging.info(f'FSM Content Message Handler ~ Catched by <{unknown_message_fsm.__name__}> func ~ From {message.from_user.id} : @{message.from_user.username}')

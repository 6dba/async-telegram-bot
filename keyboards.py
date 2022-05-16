from dataclasses import dataclass

from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton

@dataclass(frozen=False)
class Keyboards():
    
    # клавиатура - MAINMENU
    mypills = InlineKeyboardButton('Мои препараты 💊', callback_data = 'mypills')
    addplan = InlineKeyboardButton('Создать напоминание ⏱', callback_data = 'addplan')
    delplan = InlineKeyboardButton('Удалить напоминание 🗑', callback_data = 'delplan')
    confirmplan = InlineKeyboardButton('Подтвердить прием ✅', callback_data = 'planconfirm')
    edit = InlineKeyboardButton('Настройки ⚙️', callback_data= 'edit')
    main = InlineKeyboardButton('Главное меню 🏛', callback_data= 'menu')

    MainMenu_keyboard = InlineKeyboardMarkup().add(mypills)
    MainMenu_keyboard.row(addplan,confirmplan)
    MainMenu_keyboard.row(edit, delplan)


    change_time = InlineKeyboardButton('Изменить время напоминания 🕰', callback_data='edit#time')
    edit_notes = InlineKeyboardButton('Изменить примечания ✍️', callback_data='edit#note')
    edit_UTC = InlineKeyboardButton('Изменить часовой пояс 🌏', callback_data='edit#UTC')
    allday_true = InlineKeyboardButton('Напоминать в течение дня ✅',callback_data='edit#allday')
    allday_false = InlineKeyboardButton('Напоминать в течение дня',callback_data='edit#allday')
    
    edit_true_keyboard = InlineKeyboardMarkup(row_width=2).insert(change_time).insert(edit_notes).add(edit_UTC).add(allday_true).add(main)
    edit_false_keyboard = InlineKeyboardMarkup(row_width=2).insert(change_time).insert(edit_notes).add(edit_UTC).add(allday_false).add(main)


    # отдельные единичные кнопки, как Inline, так и Reply
    delete_keyboard = InlineKeyboardMarkup()
    confirm_keyboard = InlineKeyboardMarkup()
    notification_keyboard = InlineKeyboardMarkup(row_width=2).insert(main).insert(confirmplan)
    to_main_keyboard = InlineKeyboardMarkup().add(main)
    to_edit_keyboard = InlineKeyboardMarkup().add(edit)
    replMenu_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('Главное меню 🏛'))
    exit_or_add_keyboard = InlineKeyboardMarkup(row_width=2).insert(InlineKeyboardButton('Не нужно', callback_data='exit')).insert(InlineKeyboardButton('Добавить', callback_data='add'))
    skip_dose = InlineKeyboardMarkup(row_width=2).insert(main).insert(InlineKeyboardButton('Пропустить', callback_data= 'skip'))
keyboard = Keyboards()

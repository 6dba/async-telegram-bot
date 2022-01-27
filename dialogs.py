from dataclasses import dataclass

from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton

"""Диалоги бота"""


@dataclass(frozen=True)
class Messages:

    SMILE = ['🤷‍♀️','🧐','🤷‍♂️','🤔','😐','🤨','🤯','🥱','👀','👋','💊','🙅‍♀️','🎇','🗿']

    start_html: str = "Добро пожаловать, <b>{first_name}!</b> 🕺\nЯ бот, созданный для того, чтобы напоминать тебе - пора пить таблеточки!"

    help: str = """<b>Я бот - помощник!</b> 🗿\nУмею напоминать о том, что пора принимать лекарства! 🧬\n\nВ главном меню ты сможешь создать, просмотреть или редактировать напоминание 😯\n\nНажав на название препарата, можно перейти в магазин, чтобы изучить подробнее или даже купить! 💸\n\nДавай начнём, пиши: /menu 📌"""

    mainMenu: str = "🔮 Выбери действие:"

    edit: str = "🔮 Выбери действие:"

    start_addplan: str = "Я задам несколько вопросов, прошу отвечать корректно 🙆"

    drug_name_addplan: str = "Как называется препарат? 🤨"

    allday_message: str = "Напоминания будут приходить в течение дня: \n\nУтром - 08:00\nДнём - 12:00\nВечером - 18:00\n"



    idontknow: str = "<b>Я не знаю, что с этим делать</b> 🤷‍♀️\nНапомню, есть команда:  /help"

    None_pills: str = "<b>Пусто..</b>\nКажется, у тебя ещё не добавлено никаких напоминаний 🧐 \nСамое время начать!🗿"

    pills_limit: str = "Хэй-хэй, слишком много таблеточек добавляешь! \nПопробуй удалить уже оконченные курсы..🗿"

    drug_exist: str = "Думаю, такой уже есть.. "

    input_error: str = "Попробуй ввести ещё раз.. "

    input_error_time: str = "Напиши что-то в формате: <u><i>19:00</i></u> или <u><i>09:25</i></u> "

    input_unreal: str = "Хм.. Не верю.. Попробуй ввести ещё раз "

    input_more_than_need: str = "Хм.. Не думаю, что стоит пить больше, чем нужно.. Попробуй ввести ещё раз "

    input_error_dose: str = "Напиши что-то в формате: <u><i>1</i></u> или <u><i>0.25</i></u> "

    exist_drug_and_dose: str = "Думаю, препарат с данной дозировкой уже есть..  "

message = Messages()

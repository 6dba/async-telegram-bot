import logging
import sqlite3

class PillsBase:
    def __init__(self,database_file: str):
        """Подключение к БД. инит курсора"""
        self.connection = sqlite3.connect(database_file)
        self.cursor = self.connection.cursor()



    async def exist_user(self, user_id: int):
        """Проверка наличия TELEGRAM_ID в БД"""
        with self.connection:
            CHECK = self.cursor.execute("SELECT ID FROM Users WHERE TELEGRAM_ID = ?", (user_id,)).fetchall()
            return bool(len(CHECK))
    
    async def exist_drug(self, user_id: int, drug_name: str):
        """Проверка наличия лекарства в БД,
            если такой DRUG_NAME по такому TELEGRAM_ID уже есть то True"""
        with self.connection:
            CHECK = self.cursor.execute("SELECT DRUG_NAME FROM Pills WHERE DRUG_NAME = ? AND USER_ID = (SELECT ID FROM Users WHERE TELEGRAM_ID = ?)",(drug_name, user_id)).fetchall()
            return bool(len(CHECK))

    async def exist_dose(self, user_id: int, drug_name: str, dose: float):
      """
      Есть ли препарат с заданной дозировкой
      """
      with self.connection:
            CHECK = self.cursor.execute("SELECT DRUG_NAME FROM Pills WHERE DRUG_NAME = ? AND DOSE = ? AND USER_ID = (SELECT ID FROM Users WHERE TELEGRAM_ID = ?)",(drug_name, dose, user_id)).fetchall()
            return bool(len(CHECK))

    async def count_user_drugs(self, user_id: int):
        """Количество напоминаний пользователя"""
        with self.connection:
            return self.cursor.execute("SELECT COUNT(DRUG_NAME) FROM Pills WHERE USER_ID = (SELECT ID FROM Users WHERE TELEGRAM_ID = ?)", (user_id, )).fetchall()



    async def delete_user_drug(self, user_id: int, drug_name: str):
        """Удаление напоминания пользователя"""
        with self.connection:
            return self.cursor.execute("DELETE FROM Pills WHERE USER_ID = (SELECT ID FROM Users WHERE TELEGRAM_ID = ?) AND DRUG_NAME = ?", (user_id, drug_name))



    async def get_notification_mypills(self, user_id: int):
        """Вывод всех таблеток, где кол-во принятого в сутки, не равно необходимому кол-ву принятого"""
        with self.connection:
            return self.cursor.execute("SELECT * FROM Pills WHERE USER_ID = (SELECT ID FROM Users WHERE TELEGRAM_ID = ?) AND COUNT_INDAY_TAKEN != COUNT_INDAY", (user_id, )).fetchall()

    async def get_mypills(self, user_id: int):
        """Вывод всех таблеток,
            вовзращается список, к списку можно обращаться присовив обьекту (обьект[0][0] - выведется
            первый запрос по данному TELEGRAM_ID и первый элемент этого запроса)"""
        with self.connection:
            return self.cursor.execute("SELECT * FROM Pills WHERE USER_ID = (SELECT ID FROM Users WHERE TELEGRAM_ID = ?)", (user_id, )).fetchall()

    async def get_concreteness_pilldata(self, user_id: int, drug_name: str):
        """Возвращаются  данные по конкретному препарату, взаимодействие - обьект[0][x]"""

        with self.connection:
            return self.cursor.execute("SELECT * FROM Pills WHERE USER_ID = (SELECT ID FROM Users WHERE TELEGRAM_ID = ?) AND DRUG_NAME = ?", (user_id, drug_name)).fetchall()

    async def get_user_id(self, user_id: int):
        """Возвращаются ID юзера по TELEGRAM_ID"""

        with self.connection:
            return self.cursor.execute("SELECT ID FROM Users WHERE TELEGRAM_ID = ?", (user_id, )).fetchall()
    
    async def get_user_utc(self, user_id: int):
        """Возвращаются UTC юзера по TELEGRAM_ID"""

        with self.connection:
            return self.cursor.execute("SELECT UTC FROM UserUTC WHERE USER_ID = (SELECT ID FROM Users WHERE TELEGRAM_ID = ?)", (user_id, )).fetchone()

    async def get_user_allday(self, user_id: int) -> bool:
        """Возвращаются ALLDAY таблицы Users"""

        with self.connection:
            CHECK = self.cursor.execute("SELECT ALLDAY FROM Users WHERE TELEGRAM_ID = ?", (user_id,) ).fetchall()
            return bool(CHECK[0][0])
    
    async def get_join_pills_data(self, utc: int, local_user_time: str):
        """Возвращается JOIN Двух таблиц - TELEGRAM_ID, DRUG_NAME COUNT_INDAY_TAKEN, COUNT_INDAY
            При условии, что COUNT_INDAY_TAKEN != COUNT_INDAY"""

        with self.connection:
            return self.cursor.execute("SELECT DISTINCT Users.TELEGRAM_ID, DRUG_NAME, COUNT_INDAY_TAKEN, COUNT_INDAY FROM Pills INNER JOIN Users, UserUTC ON Pills.USER_ID = Users.ID AND Pills.USER_ID = UserUTC.USER_ID WHERE (UserUTC.UTC = ? AND Pills.TIME = ? AND COUNT_INDAY_TAKEN != COUNT_INDAY AND Users.ALLDAY = 1 AND Pills.TIME != '08:00' AND Pills.TIME != '12:00' AND Pills.TIME != '18:00') OR (UserUTC.UTC = ? AND Pills.TIME = ? AND COUNT_INDAY_TAKEN != COUNT_INDAY AND Users.ALLDAY = 0)", (utc, local_user_time, utc, local_user_time)).fetchall()

    async def get_allday_users(self, utc: int):
        """Возвращаются TELEGRAM_ID юзеров, где ALLDAY = 1 и COUNT_INDAY_TAKEN != COUNT_INDAY """
        with self.connection:
            return self.cursor.execute("SELECT DISTINCT Users.TELEGRAM_ID FROM Pills INNER JOIN Users, UserUTC ON Pills.USER_ID = Users.ID AND Pills.USER_ID = UserUTC.USER_ID WHERE (UserUTC.UTC = ?) AND COUNT_INDAY_TAKEN != COUNT_INDAY AND Users.ALLDAY = 1", (utc, )).fetchall()

    async def get_main_message_id(self, user_id: int):
        """Возвращается ID сообщения с главным меню, дабы их не плодить"""
        with self.connection:
            return self.cursor.execute("SELECT MAIN_MESSAGE_ID FROM Users WHERE TELEGRAM_ID = ?", (user_id, )).fetchone()



    async def insert_new_user(self, user_id: int):
        """Добавление нового пользователя"""
        with self.connection:
            return self.cursor.execute("INSERT INTO Users (TELEGRAM_ID) VALUES (?)", (user_id,))

    async def insert_new_data(self, user_id: int, drug_name: str, course_taken: int, course_taking: int, count_day: int, dose: float, time: str, note: str):
        """Добавление нового юзера (ПОЛНЫЙ ФАРШ). Не знаю зачем я ее добавил, но пусть будет"""
        with self.connection:
            ID = await self.get_user_id(user_id)
            return self.cursor.execute("INSERT INTO Pills (USER_ID, DRUG_NAME, COURSE_TAKEN, COURSE_TAKING, COUNT_INDAY, DOSE, TIME, NOTE) VALUES (?,?,?,?,?,?,?,?)",(ID[0][0], drug_name, course_taken, course_taking, count_day, dose, time, note))
 


    async def set_course_taken(self, user_id: int, drug_name: str, course_taken: int):
        """Изменениe значения пройденного дня курса"""
        with self.connection:
            return self.cursor.execute("UPDATE Pills SET COURSE_TAKEN = ? WHERE USER_ID = (SELECT ID FROM Users WHERE TELEGRAM_ID = ?) AND DRUG_NAME = ?", (course_taken, user_id, drug_name))
    
    async def set_countInDay_taken(self, user_id: int, drug_name: str, countInDay_taken: int):
        """Изменениe значения принятых таблеток в день"""
        with self.connection:
            return self.cursor.execute("UPDATE Pills SET COUNT_INDAY_TAKEN = ? WHERE USER_ID = (SELECT ID FROM Users WHERE TELEGRAM_ID = ?) AND DRUG_NAME = ?", (countInDay_taken, user_id, drug_name))
    
    async def set_note(self, user_id: int, drug_name: str, note: str):
        """Изменениe значения заметок"""
        with self.connection:
            return self.cursor.execute("UPDATE Pills SET NOTE = ? WHERE USER_ID = (SELECT ID FROM Users WHERE TELEGRAM_ID = ?) AND DRUG_NAME = ?", (note, user_id, drug_name))
    
    async def set_time(self, user_id: int, hh_mm: str, drug_name: str):
        """Изменениe значения времени"""
        with self.connection:
            return self.cursor.execute("UPDATE Pills SET TIME = ? WHERE USER_ID = (SELECT ID FROM Users WHERE TELEGRAM_ID = ?) AND DRUG_NAME = ?", (hh_mm, user_id, drug_name))

    async def set_utc(self, user_id: int, utc: int):
        """Изменениe значения заметок"""
        with self.connection:
            ID = await self.get_user_id(user_id)
            return self.cursor.execute("INSERT INTO UserUTC (USER_ID,UTC) VALUES (?,?)", (ID[0][0], utc))
        
    async def set_allday(self, user_id: int, value: bool):
        """Напоминать в течение дня? (утро, день, вечер) Да - True or 1"""
        with self.connection:
            return self.cursor.execute("UPDATE Users SET ALLDAY = ? WHERE TELEGRAM_ID = ?", (value, user_id))
    
    async def set_allcount_inday_to_null(self, utc: int):
        """Функция для зануления кол-ва принятого в день, когда local user time = 00:00"""
        with self.connection:
            return self.cursor.execute("UPDATE Pills SET COUNT_INDAY_TAKEN = 0 WHERE EXISTS (SELECT USER_ID FROM UserUTC WHERE UserUTC.UTC = ?)", (utc, ))

    async def set_main_message_id(self, message_id: int, user_id: int):
        """Сетаем ID сообщения главного меню"""
        with self.connection:
            return self.cursor.execute("UPDATE Users SET MAIN_MESSAGE_ID = ? WHERE TELEGRAM_ID = ?", (message_id,user_id))
    
    def close_connection(self):
        self.connection.close()

database_ = PillsBase('TTTP_bot.db')

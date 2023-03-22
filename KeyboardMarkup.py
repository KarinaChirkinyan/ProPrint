from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


cancelkey = InlineKeyboardButton(text="Отмена", callback_data="cancel")
cancelboard = InlineKeyboardMarkup()
cancelboard.add(cancelkey)

key1 = InlineKeyboardButton(text="Односторонняя", callback_data="1")
key2 = InlineKeyboardButton(text="Двусторонная", callback_data="2")
board = InlineKeyboardMarkup()
board.add(key1)
board.add(key2)
board.add(cancelkey)

double_key1 = InlineKeyboardButton(text="Короткий край", callback_data="3")
double_key2 = InlineKeyboardButton(text="Длинный край", callback_data="4", )
double_board = InlineKeyboardMarkup()
double_board.add(double_key1)
double_board.add(double_key2)
double_board.add(cancelkey)

page1 = InlineKeyboardButton(text="Да", callback_data="Yes")
page2 = InlineKeyboardButton(text="Нет", callback_data="No")
page_board = InlineKeyboardMarkup()
page_board.add(page1)
page_board.add(page2)
page_board.add(cancelkey)

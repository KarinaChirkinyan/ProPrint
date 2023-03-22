import PyPDF2
import telebot
from telebot import types
import config
from datetime import date
import os
import pandas as pd
import openpyxl
import requests
from pathlib import Path
from PyPDF2 import PdfReader

import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


bot = telebot.TeleBot(config.Token)
max_kol = 250  # максимальное количество в лотке
kol_str = max_kol  # текущее значение в лотке
subscribe = []

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("🔔 Подключить уведомления")
    markup.add(btn1)
    bot.send_message(message.chat.id,
                     text="Привет! Я бот тех.поддержки ProPrint", reply_markup=markup)


@bot.message_handler(content_types=['text'])
def func(message):
    global kol_str, max_kol, subscribe

    if (message.text == "🔔 Подключить уведомления"):
        subscribe.append(message)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Проверить остаток бумаги")
        btn2 = types.KeyboardButton("Ресурсы")
        btn3 = types.KeyboardButton("❓ Задать вопрос")
        markup.add(btn1, btn2, btn3)
        bot.send_message(message.chat.id,
                         text="Уведомления об окончании ресурсов подключены.", reply_markup=markup)

    elif (message.text == "Проверить остаток бумаги"):
        bot.send_message(message.chat.id, text=f"Количество листов в принтере: {kol_str}")

    elif (message.text == "Ресурсы"):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Заполнил лоток для бумаги")
        btn2 = types.KeyboardButton("Заменил картридж")
        btn3 = types.KeyboardButton("Отчет")
        back = types.KeyboardButton("Вернуться в главное меню")
        markup.add(btn1, btn2, btn3, back)
        bot.send_message(message.chat.id, text='Выберите действие', reply_markup=markup)

    elif (message.text == "Заполнил лоток для бумаги"):
        kol_str = max_kol
        bot.send_message(message.chat.id, text=f"Количество листов в принтере: {kol_str}")

    elif (message.text == "Заменил картридж"):
        current_date = date.today()
        wb = openpyxl.load_workbook("Отчет.xlsx")
        sheet = wb.active
        sheet.append((current_date, "Замена картриджа"))
        wb.save("Отчет.xlsx")
        bot.send_message(message.chat.id, text=f"{current_date}: Замена картриджа")

    elif (message.text == "Отчет"):
        f = open("Отчет.xlsx", "rb")
        bot.send_document(message.chat.id, f)

    elif (message.text == "Вернуться в главное меню"):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Проверить остаток бумаги")
        btn2 = types.KeyboardButton("Ресурсы")
        btn3 = types.KeyboardButton("❓ Задать вопрос")
        markup.add(btn1, btn2, btn3)
        bot.send_message(message.chat.id, text="Вы вернулись в главное меню", reply_markup=markup)

    elif (message.text == "❓ Задать вопрос"):
        bot.send_message(message.chat.id, text="По всем вопросам обращаться к @realsamvel")

    elif (message.text == "Уведомление"):
        bot.send_message(message.chat.id, text=f"Осталось мало бумаги! Количество листов в принтере: {kol_str}")


class EventHandler(FileSystemEventHandler):
    # вызывается на событие создания файла или директории
    def on_created(self, event):
        global kol_str, max_kol, subscribe
        file = event.src_path
        reader = PdfReader(file)
        kol_str -= len(reader.pages)

        if kol_str <= int(max_kol * 0.15):
            for i in subscribe:
                i.text = "Уведомление"
                func(i)

    """
    # вызывается на событие модификации файла или директории
    def on_modified(self, event):
        print(event.event_type, event.src_path)

    # вызывается на событие удаления файла или директории
    def on_deleted(self, event):
        print(event.event_type, event.src_path)

    # вызывается на событие перемещения\переименования файла или директории
    def on_moved(self, event):
        print(event.event_type, event.src_path, event.dest_path)
    """

if __name__ == "__main__":
    path = r"...\ProPrintFiles"  # отслеживаемая директория
    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            bot.polling(none_stop=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

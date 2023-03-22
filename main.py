import win32api

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.types.message import ContentType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import json

from docx2pdf import convert

from yookassa import Configuration, Payment

import KeyboardMarkup
import logging
import PyPDF2
import os
import win32print
import config
import asyncio


class stt(StatesGroup):
    Path = State()
    AllPages = State()
    Orient = State()
    BoolPages = State()
    StartPage = State()
    EndPage = State()
    Copies = State()
    Print = State()


Token = config.Token
Configuration.account_id = config.ShopId
Configuration.secret_key = config.PaymentsToken

logging.basicConfig(level=logging.INFO)

bot = Bot(token=Token)
dp = Dispatcher(bot, storage=MemoryStorage())


async def print_file(data):
    name = win32print.GetDefaultPrinter()
    printdefaults = {"DesiredAccess": win32print.PRINTER_ALL_ACCESS}
    ## начинаем работу с принтером ("открываем" его)
    handle = win32print.OpenPrinter(name, printdefaults)
    ## Если изменить level на другое число, то не сработает
    level = 2
    ## Получаем значения принтера
    attributes = win32print.GetPrinter(handle, level)
    ## Настройка двухсторонней печати
    attributes['pDevMode'].Duplex = data["Orient"]  # flip over  3 - это короткий 2 - это длинный край
    attributes['pDevMode'].Copies = data["Copies"]
    ## Передаем нужные значения в принтер
    win32print.SetPrinter(handle, level, attributes, 0)
    win32print.GetPrinter(handle, level)['pDevMode'].Duplex
    ## Предупреждаем принтер о старте печати
    win32print.StartDocPrinter(handle, 1, [data["Path"], None, "raw"])
    ## 2 в начале для открытия pdf и его сворачивания, для открытия без сворачивания поменяйте на 1
    win32api.ShellExecute(2, 'print', data["Path"], '.', '/manualstoprint', 0)
    ## "Закрываем" принтер
    win32print.ClosePrinter(handle)


def print_photo(path):
    os.startfile(path, "print")


@dp.message_handler(state=stt.Copies)
async def buy(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["Copies"] = int(message.text)

        if data["Orient"] > 1:
            Price = data["Copies"] * data["AllPages"] * 8
        if data["AllPages"] <= 15:
            Price = data["Copies"] * data["AllPages"] * 7
        if data["AllPages"] > 15:
            Price = data["Copies"] * data["AllPages"] * 5

        payment = Payment.create({
            "amount": {
                "value": float(Price),
                "currency": "RUB"
            },
            "payment_method_data": {
                "type": "bank_card"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "google.com"
            },
            "capture": True,
            "description": f"Оплата {data['AllPages']} страниц"
        })

        payment_data = json.loads(payment.json())
        payment_id = payment_data['id']
        payment_url = (payment_data['confirmation'])['confirmation_url']

        pay = InlineKeyboardButton(text="Оплатить", url=payment_url, callback_data="print")
        pay_board = InlineKeyboardMarkup()
        pay_board.add(pay)
        pay_board.add(KeyboardMarkup.cancelkey)
        await message.answer(f'Оплатите {Price} рублей за печать {data["AllPages"] * data["Copies"]} страниц', reply_markup=pay_board)

        payment = json.loads((Payment.find_one(payment_id)).json())

        while payment['status'] == 'pending':
            payment = json.loads((Payment.find_one(payment_id)).json())
            await asyncio.sleep(3)

        if payment['status'] == 'succeeded':
            print("SUCCSESS RETURN")
            await message.answer("✅Cпасибо, что воспользовались нашим сервисом, если хотите напечатать что-то еще просто пришлите файл")
            await print_file({"Orient": data["Orient"], "Copies": data["Copies"], "Path": data["Path"]})

            await state.finish()
            print(payment)
        else:
            print("BAD RETURN")
            print(payment)

            cur_state = await state.get_state()
            if cur_state is None:
                return

            await state.finish()


@dp.message_handler(commands=['start'])
async def start_message(message):
    await bot.send_message(message.chat.id, "Привет, я распечатаю файл который ты пришлешь формата .docx и .pdf")


@dp.message_handler(content_types=['photo'])
async def get_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        file_info = await bot.get_file(message.photo[len(message.photo) - 1].file_id)
        downloaded_file = await bot.download_file(file_info.file_path)

        src = 'C:/Users/basso/Desktop/ProPrintFiles/' + file_info.file_path
        with open(src, 'wb') as new_file:
            new_file.write(downloaded_file.getvalue())

        await print_photo(src)


@dp.message_handler(content_types=['document'])
async def get_file(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        file = await bot.get_file(message.document.file_id)
        file_path = file.file_path

        if file_path[-4:] == "docx":
            data["Path"] = f'C:\\Users\\Oleg\\Desktop\\ProPrintFiles\\{message.document.file_id}.docx'
        elif file_path[-3:] == "doc":
            data["Path"] = f'C:\\Users\\Oleg\\Desktop\\ProPrintFiles\\{message.document.file_id}.doc'
        else:
            data["Path"] = f'C:\\Users\\Oleg\\Desktop\\ProPrintFiles\\{message.document.file_id}.pdf'
        await bot.download_file(file_path, data["Path"])

        if file_path[-3:] != "pdf":
            convert(data["Path"], f'C:\\Users\\Oleg\\Desktop\\ProPrintFiles\\{message.document.file_id}.pdf')
            os.remove(data["Path"])
            data["Path"] = f'C:\\Users\\Oleg\\Desktop\\ProPrintFiles\\{message.document.file_id}.pdf'

        data["AllPages"] = len(PyPDF2.PdfReader(data["Path"]).pages)
        await message.answer("Выберете ориентацию страниц", reply_markup=KeyboardMarkup.board)


@dp.callback_query_handler(lambda c: c.data == "1")
async def orient_page(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    async with state.proxy() as data:
        data["Orient"] = 1

    await stt.BoolPages.set()
    await call.message.edit_text(text="Напечатать все страницы?", reply_markup=KeyboardMarkup.page_board)


@dp.callback_query_handler(lambda c: c.data == "2")
async def orient_page_double(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_reply_markup(reply_markup=KeyboardMarkup.double_board)


@dp.callback_query_handler(lambda c: c.data == "3")
async def orient_page_double_short(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    async with state.proxy() as data:
        data["Orient"] = 3

    await stt.BoolPages.set()
    await call.message.edit_text(text="Напечатать все страницы?", reply_markup=KeyboardMarkup.page_board)


@dp.callback_query_handler(lambda c: c.data == "4")
async def orient_page_double_long(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    async with state.proxy() as data:
        data["Orient"] = 2

    await stt.BoolPages.set()
    await call.message.edit_text(text="Напечатать все страницы?", reply_markup=KeyboardMarkup.page_board)


@dp.callback_query_handler(lambda c: c.data == "Yes", state=stt.BoolPages)
async def pages_num(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data["BoolPages"] = False

    await call.answer()
    await stt.Copies.set()
    await call.message.edit_text(text="Введите количество копий")


@dp.callback_query_handler(lambda c: c.data == "No", state=stt.BoolPages)
async def start_page_num(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await stt.StartPage.set()
    async with state.proxy() as data:
        await call.message.edit_text(text=f"Введите начальную страницу (Всего страниц: {data['AllPages']})", reply_markup=KeyboardMarkup.cancelboard)


@dp.message_handler(lambda mes: not mes.text.isdigit(), state=stt.StartPage)
async def start_page_invalid(mes: types.Message, state: FSMContext):
    return await mes.reply("Номер страницы должен быть цифрой. Укажите количество копий.")


@dp.message_handler(lambda mes: int(mes.text) < 0, state=stt.StartPage)
async def start_page_invalid(mes: types.Message, state: FSMContext):
    return await mes.reply("Номер страницы должен быть положительной цифрой. Укажите количество копий.")


@dp.message_handler(state=stt.StartPage)
async def end_page_num(mes: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['StartPage'] = int(mes.text)
        await mes.answer(text=f"Введите конечную страницу (Всего страниц: {data['AllPages']})", reply_markup=KeyboardMarkup.cancelboard)
        await stt.EndPage.set()


@dp.message_handler(lambda mes: not mes.text.isdigit(), state=stt.EndPage)
async def end_page_invalid(mes: types.Message, state: FSMContext):
    return await mes.reply("Номер страницы должен быть цифрой. Укажите количество копий.")


@dp.message_handler(lambda mes: int(mes.text) < 0, state=stt.EndPage)
async def start_page_invalid(mes: types.Message, state: FSMContext):
    return await mes.reply("Номер страницы должен быть положительной цифрой. Укажите количество копий.")


@dp.message_handler(state=stt.EndPage)
async def cut_file(mes: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['EndPage'] = int(mes.text)
        flag = True
        if data["AllPages"] < data["EndPage"]:
            await mes.answer("Промежуток страниц указан некорректно, укажите начальную страницу")
            await stt.StartPage.set()
            flag = False
        if data["StartPage"] > data["AllPages"] and flag:
            await mes.answer("Промежуток страниц указан некорректно, укажите начальную страницу")
            await stt.StartPage.set()
            flag = False
        if data["StartPage"] > data["EndPage"] and flag:
            await mes.answer("Промежуток страниц указан некорректно, укажите начальную страницу")
            await stt.StartPage.set()
            flag = False
        if flag:
            reader = PyPDF2.PdfReader(data["Path"])
            new_path = data["Path"][:-4] + ".pdf"
            writer = PyPDF2.PdfWriter()

            for i in range(data["StartPage"] - 1, data["EndPage"]):
                writer.add_page(reader.pages[i])

            with open(new_path, "wb") as new_file:
                writer.write(new_file)

            data["Path"] = new_path
            data["AllPages"] = data["EndPage"] - data["StartPage"] + 1

            await mes.answer("Введите количество копий")
            await stt.next()


@dp.message_handler(lambda mes: not mes.text.isdigit(), state=stt.Copies)
async def copies_invalid(mes: types.Message, state: FSMContext):
    return await mes.reply("Количество копий должно быть цифрой. Укажите количество копий.")


@dp.callback_query_handler(lambda c: c.data == "cancel", state='*')
async def cancel(call: types.CallbackQuery, state: FSMContext):
    cur_state = await state.get_state()
    if cur_state is None:
        await call.answer()
        await call.message.edit_text(text="Мы сожалеем, что пошло что-то не так, чтобы продолжить работу просто отправьте файл!")
    else:
        await state.finish()
        await call.answer()
        await call.message.edit_text(text="Мы сожалеем, что пошло что-то не так, чтобы продолжить работу просто отправьте файл!")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=False)

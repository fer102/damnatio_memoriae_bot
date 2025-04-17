import asyncio
from datetime import datetime, timedelta, date
from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "8091281268:AAHlyXIf4EA4pBw4xba1lajIOGGWEDUU9tU"
bot = Bot(token=TOKEN)
dp = Dispatcher()

user_data = {}         # user_id -> list of reminders
in_progress = {}       # Temporary data during creation
reminder_history = {}  # user_id -> list of fired reminders

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    await message.answer("О чём вам напомнить, господин?")
    in_progress[user_id] = {}

@dp.message(Command("list"))
async def cmd_list(message: Message):
    user_id = message.from_user.id
    reminders = user_data.get(user_id, [])
    if not reminders:
        await message.answer("У вас нет активных напоминаний, господин.")
        return
    msg = "Ваши напоминания:\n"
    for i, r in enumerate(reminders, 1):
        dt = r['time'].strftime('%d.%m.%Y %H:%M')
        msg += f"{i}. 🕰 {dt} — {r['text']}\n"
    await message.answer(msg)

@dp.message(Command("history"))
async def cmd_history(message: Message):
    user_id = message.from_user.id
    history = reminder_history.get(user_id, [])
    if not history:
        await message.answer("История пуста, господин.")
        return
    msg = "Прошедшие напоминания:\n"
    for r in history:
        dt = r['time'].strftime('%d.%m.%Y %H:%M')
        msg += f"🕰 {dt} — {r['text']}\n"
    await message.answer(msg)

@dp.message(Command("delete"))
async def cmd_delete(message: Message):
    user_id = message.from_user.id
    reminders = user_data.get(user_id, [])
    if not reminders:
        await message.answer("Нет напоминаний для удаления, господин.")
        return
    builder = InlineKeyboardBuilder()
    for i, r in enumerate(reminders):
        label = f"Удалить {i + 1} ({r['time'].strftime('%d.%m %H:%M')})"
        builder.button(text=label, callback_data=f"delete_{i}")
    builder.adjust(1)
    await message.answer("Выберите напоминание для удаления:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("delete_"))
async def confirm_delete(callback: CallbackQuery):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[1])
    reminders = user_data.get(user_id, [])
    if idx < len(reminders):
        removed = reminders.pop(idx)
        await callback.message.answer(f"Удалено: {removed['text']} ({removed['time'].strftime('%d.%m %H:%M')})")
    else:
        await callback.message.answer("Неверный индекс напоминания.")
    await callback.answer()

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message):
    user_data[message.from_user.id] = []
    await message.answer("Все напоминания отменены, господин.")

@dp.message(F.text)
async def handle_text(message: Message):
    user_id = message.from_user.id
    if user_id in in_progress and 'date' in in_progress[user_id]:
        try:
            time_obj = datetime.strptime(message.text.strip(), "%H:%M").time()
            selected_date = in_progress[user_id]['date']
            reminder_dt = datetime.combine(selected_date, time_obj)
            text = in_progress[user_id]['text']
            reminder = {"text": text, "time": reminder_dt}
            user_data.setdefault(user_id, []).append(reminder)
            asyncio.create_task(schedule_reminder(user_id, reminder))
            await message.answer(f"Превосходно. Я напомню вам:\n📝 *{text}*\n📅 {reminder_dt.strftime('%d.%m.%Y в %H:%M')}", parse_mode="Markdown")
            del in_progress[user_id]
        except ValueError:
            await message.answer("Пожалуйста, введите время в формате ЧЧ:ММ, например: 14:30")
        return

    in_progress[user_id] = {'text': message.text}
    await message.answer("Выберите дату, господин:", reply_markup=date_picker_keyboard())

@dp.callback_query(F.data.startswith("date_"))
async def handle_date(callback: CallbackQuery):
    user_id = callback.from_user.id
    date_str = callback.data.split("_")[1]
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    in_progress[user_id]['date'] = selected_date
    await callback.message.answer("Теперь, господин, введите время в формате ЧЧ:ММ (например, 14:30)")
    await callback.answer()

async def schedule_reminder(user_id: int, reminder: dict):
    delay = (reminder['time'] - datetime.now()).total_seconds()
    if delay > 0:
        await asyncio.sleep(delay)

    sent = await bot.send_message(user_id, f"🔔 Напоминание: {reminder['text']}")

    # Добавляем в историю
    reminder_history.setdefault(user_id, []).append(reminder)

    # Проверка на прочтение через 5 минут
    await asyncio.sleep(300)
    try:
        status = await bot.get_chat_member(user_id, user_id)
        if sent and not sent.is_topic_message:
            await bot.send_message(user_id, f"🔔 Повторное напоминание: {reminder['text']}")
    except Exception:
        pass

def date_picker_keyboard():
    builder = InlineKeyboardBuilder()
    today = date.today()
    for i in range(14):
        d = today + timedelta(days=i)
        builder.button(text=d.strftime("%d.%m.%Y"), callback_data=f"date_{d.isoformat()}")
    builder.adjust(2)
    return builder.as_markup()

async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Создать новое напоминание"),
        BotCommand(command="list", description="Показать активные напоминания"),
        BotCommand(command="delete", description="Удалить одно напоминание"),
        BotCommand(command="history", description="Показать историю напоминаний"),
        BotCommand(command="cancel", description="Удалить все напоминания")
    ]
    await bot.set_my_commands(commands)

if __name__ == "__main__":
    async def main():
        await set_bot_commands()
        await dp.start_polling(bot)

    asyncio.run(main())

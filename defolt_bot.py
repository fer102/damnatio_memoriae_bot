import asyncio
from datetime import datetime, timedelta, date
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "8091281268:AAHlyXIf4EA4pBw4xba1lajIOGGWEDUU9tU"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Структура: user_id -> список напоминаний
user_data = {}

# Словарь для хранения напоминаний в процессе ввода
in_progress = {}

# /start — начало диалога
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    await message.answer("О чём вам напомнить, господин?")
    in_progress[user_id] = {}

# /list — показать список напоминаний
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

# /cancel — удалить все напоминания
@dp.message(Command("cancel"))
async def cmd_cancel(message: Message):
    user_id = message.from_user.id
    user_data[user_id] = []
    await message.answer("Все напоминания отменены, господин.")

# Получаем текст или время
@dp.message(F.text)
async def handle_text(message: Message):
    user_id = message.from_user.id

    # Ввод времени
    if user_id in in_progress and 'date' in in_progress[user_id]:
        try:
            time_obj = datetime.strptime(message.text.strip(), "%H:%M").time()
            selected_date = in_progress[user_id]['date']
            reminder_dt = datetime.combine(selected_date, time_obj)
            text = in_progress[user_id]['text']

            # Добавляем напоминание
            reminder = {"text": text, "time": reminder_dt}
            user_data.setdefault(user_id, []).append(reminder)
            asyncio.create_task(schedule_reminder(user_id, reminder))

            await message.answer(
                f"Превосходно. Я напомню вам:\n📝 *{text}*\n📅 {reminder_dt.strftime('%d.%m.%Y в %H:%M')}",
                parse_mode="Markdown"
            )
            del in_progress[user_id]

        except ValueError:
            await message.answer("Пожалуйста, введите время в формате ЧЧ:ММ, например: 14:30")
        return

    # Ввод текста
    in_progress[user_id] = {'text': message.text}
    await message.answer("Выберите дату, господин:", reply_markup=date_picker_keyboard())

# Обработка выбора даты
@dp.callback_query(F.data.startswith("date_"))
async def handle_date(callback: CallbackQuery):
    user_id = callback.from_user.id
    date_str = callback.data.split("_")[1]
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    if user_id in in_progress:
        in_progress[user_id]['date'] = selected_date
        await callback.message.answer("Теперь, господин, введите время в формате ЧЧ:ММ (например, 14:30)")
    await callback.answer()

# Планирование напоминания
async def schedule_reminder(user_id: int, reminder: dict):
    delay = (reminder['time'] - datetime.now()).total_seconds()
    if delay > 0:
        await asyncio.sleep(delay)

    await bot.send_message(
        user_id,
        f"🔔 Напоминание: {reminder['text']}",
        reply_markup=remind_again_button(reminder)
    )

# Кнопка "Повторить"
def remind_again_button(reminder):
    builder = InlineKeyboardBuilder()
    time_str = reminder['time'].isoformat()
    builder.button(
        text="🔁 Напомнить ещё раз через 10 минут",
        callback_data=f"remind_again|{time_str}"
    )
    return builder.as_markup()

# Обработка повторного напоминания
@dp.callback_query(F.data.startswith("remind_again"))
async def handle_repeat(callback: CallbackQuery):
    user_id = callback.from_user.id
    _, time_str = callback.data.split("|")

    dt = datetime.fromisoformat(time_str)
    reminder_list = user_data.get(user_id, [])
    found = next((r for r in reminder_list if r['time'] == dt), None)

    if found:
        await callback.answer("Напомню ещё раз через 10 минут, господин.")
        await asyncio.sleep(600)
        await bot.send_message(
            user_id,
            f"🔔 Напоминание (повтор): {found['text']}",
            reply_markup=remind_again_button(found)
        )
    else:
        await callback.answer("Не удалось найти это напоминание.")

# Календарь на 14 дней
def date_picker_keyboard():
    builder = InlineKeyboardBuilder()
    today = date.today()
    for i in range(14):
        d = today + timedelta(days=i)
        builder.button(text=d.strftime("%d.%m.%Y"), callback_data=f"date_{d.isoformat()}")
    builder.adjust(2)
    return builder.as_markup()

# Устанавливаем команды бота
async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Создать новое напоминание"),
        BotCommand(command="list", description="Показать активные напоминания"),
        BotCommand(command="cancel", description="Удалить все напоминания"),
    ]
    await bot.set_my_commands(commands)

# Запуск бота
if __name__ == "__main__":
    async def main():
        await set_bot_commands()
        await dp.start_polling(bot)

    asyncio.run(main())

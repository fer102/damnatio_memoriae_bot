import asyncio
from datetime import datetime, timedelta, date
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "8091281268:AAHlyXIf4EA4pBw4xba1lajIOGGWEDUU9tU"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Временное хранилище данных
user_data = {}

# /start — приветствие
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    user_data[user_id] = {}
    await message.answer("О чём вам напомнить, господин?")

# Получаем текст напоминания или время
@dp.message(F.text)
async def get_reminder_text_or_time(message: Message):
    user_id = message.from_user.id

    # Если ожидаем время
    if user_id in user_data and 'waiting_for_time' in user_data[user_id]:
        time_text = message.text.strip()
        try:
            time_obj = datetime.strptime(time_text, "%H:%M").time()
            selected_date = user_data[user_id]['date']
            reminder_dt = datetime.combine(selected_date, time_obj)

            user_data[user_id]['reminder_time'] = reminder_dt

            await message.answer(
                f"Превосходно. Я напомню вам:\n📝 *{user_data[user_id]['text']}*\n📅 {reminder_dt.strftime('%d.%m.%Y в %H:%M')}",
                parse_mode="Markdown"
            )

            asyncio.create_task(schedule_reminder(user_id))
            del user_data[user_id]['waiting_for_time']

        except ValueError:
            await message.answer("Пожалуйста, укажите время в формате ЧЧ:ММ, например: 14:30")
        return

    # Иначе — сохраняем текст и просим выбрать дату
    user_data[user_id]['text'] = message.text
    await message.answer("Выберите дату, господин:", reply_markup=date_picker_keyboard())

# Обработка выбора даты
@dp.callback_query(F.data.startswith("date_"))
async def process_date(callback: CallbackQuery):
    user_id = callback.from_user.id
    date_str = callback.data.split("_")[1]
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    user_data[user_id]['date'] = selected_date
    user_data[user_id]['waiting_for_time'] = True

    await callback.message.answer(
        "Теперь, господин, укажите время в формате ЧЧ:ММ (например, 14:30)"
    )
    await callback.answer()

# Планировщик напоминания
async def schedule_reminder(user_id: int):
    reminder_time: datetime = user_data[user_id]['reminder_time']
    now = datetime.now()
    delay = (reminder_time - now).total_seconds()

    if delay > 0:
        await asyncio.sleep(delay)

    text = user_data[user_id]['text']
    await bot.send_message(
        user_id,
        f"🔔 Напоминание: {text}",
        reply_markup=remind_again_button()
    )

# Кнопка "Напомнить ещё раз"
def remind_again_button():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔁 Напомнить ещё раз через 10 минут", callback_data="remind_again")
    return builder.as_markup()

# Обработка повторного напоминания
@dp.callback_query(F.data == "remind_again")
async def repeat_reminder(callback: CallbackQuery):
    user_id = callback.from_user.id
    text = user_data.get(user_id, {}).get('text')

    if not text:
        await callback.answer("Прошу прощения, но я не помню, о чём нужно было напомнить.")
        return

    await callback.answer("Напомню ещё раз через 10 минут, господин.")
    await asyncio.sleep(600)  # 10 минут
    await bot.send_message(
        user_id,
        f"🔔 Напоминание (повтор): {text}",
        reply_markup=remind_again_button()
    )

# Генератор кнопок с датами
def date_picker_keyboard():
    builder = InlineKeyboardBuilder()
    today = date.today()
    for i in range(14):  # 14 дней вперёд
        d = today + timedelta(days=i)
        btn_text = d.strftime("%d.%m.%Y")
        builder.button(text=btn_text, callback_data=f"date_{d.isoformat()}")
    builder.adjust(2)
    return builder.as_markup()

# Запуск
if __name__ == "__main__":
    dp.run_polling(bot)

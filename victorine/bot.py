import sqlite3
import random
import logging
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)

# Настройка путей
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
LOG_PATH = os.path.join(BASE_DIR, "logs", "bot.log")
QUESTIONS_PATH = os.path.join(BASE_DIR, "quiz_data.json")

# Настройка логов
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Токен вашего бота
TOKEN = "7840043878:AAGdk0KsQGubiOxSRMh_UphOOUrqMiDbutU"

# Множители для рулетки
roulette_multipliers = [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1, 1.1, 1.25, 1.5, 1.75, 2, 3, 10]

# Загрузка вопросов из JSON
def load_questions():
    try:
        with open(QUESTIONS_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data["directions"]
    except Exception as e:
        logger.error(f"Ошибка при загрузке вопросов: {e}")
        return {}

quiz_data = load_questions()

# Проверка наличия вопросов
if not quiz_data:
    logger.error("Не найдено вопросов в файле quiz_data.json")
    exit(1)

# Подключение к базе данных
def get_db_connection():
    return sqlite3.connect(DB_PATH)

# Инициализация базы данных
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            score INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1
        )
        """
    )
    conn.commit()
    conn.close()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
        (user_id, username),
    )
    conn.commit()
    conn.close()

    # Формируем список доступных направлений
    keyboard = [
        [InlineKeyboardButton(f"🎯 {quiz_data[direction]['name']}", callback_data=f"dir_{direction}")]
        for direction in quiz_data.keys()
    ]
    
    await update.message.reply_text(
        "🎉 Добро пожаловать в викторину!\n\n"
        "Выберите направление:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Обработка выбора направления
async def handle_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    direction = query.data.replace("dir_", "")
    
    if direction not in quiz_data:
        await query.message.reply_text("❌ Направление не найдено")
        return
    
    # Создаем кнопки для тем
    keyboard = [
        [InlineKeyboardButton(
            f"📚 {quiz_data[direction]['topics'][topic]['name']}",
            callback_data=f"topic_{direction}_{topic}"
        )]
        for topic in quiz_data[direction]["topics"].keys()
    ]
    
    await query.edit_message_text(
        f"Выберите тему в разделе {quiz_data[direction]['name']}:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Обработка выбора темы
async def handle_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, direction, topic = query.data.split("_")
    
    if direction not in quiz_data or topic not in quiz_data[direction]["topics"]:
        await query.message.reply_text("❌ Тема не найдена")
        return
    
    # Выбираем случайный квиз из темы
    quizzes = quiz_data[direction]["topics"][topic]["quizzes"]
    selected_quiz = random.choice(quizzes)
    
    # Сохраняем данные в контексте
    context.user_data["questions"] = selected_quiz["questions"]
    context.user_data["current_question"] = 0
    context.user_data["score"] = 0
    context.user_data["quiz_title"] = selected_quiz.get("title", "Викторина")
    
    await ask_question(update, context)

# Задать вопрос с кнопками
async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    
    questions = context.user_data["questions"]
    current_idx = context.user_data["current_question"]
    
    if current_idx >= len(questions):
        final_score = context.user_data["score"]
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🏆 Викторина '{context.user_data['quiz_title']}' завершена!\nВаш счет: {final_score}"
        )
        update_user_score(update.effective_user.id, final_score)
        return

    question_data = questions[current_idx]
    question = question_data["question"]
    answers = question_data["answers"]
    correct_idx = question_data["correct_answer"]
    
    # Сохраняем индекс правильного ответа
    context.user_data["correct_index"] = correct_idx
    context.user_data["current_explanation"] = question_data.get("explanation", "")
    
    # Создаем кнопки
    keyboard = [
        [InlineKeyboardButton(answer, callback_data=f"ans_{i}")]
        for i, answer in enumerate(answers)
    ]
    
    if query:
        await query.edit_message_text(
            text=f"❓ Вопрос {current_idx + 1}/{len(questions)}:\n\n{question}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❓ Вопрос {current_idx + 1}/{len(questions)}:\n\n{question}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Обработка ответа
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_choice = int(query.data.split("_")[1])
    correct_idx = context.user_data["correct_index"]
    explanation = context.user_data["current_explanation"]
    
    if user_choice == correct_idx:
        context.user_data["score"] += 10
        response = "✅ Правильно! +10 баллов"
    else:
        correct_answer = query.message.reply_markup.inline_keyboard[correct_idx][0].text
        response = f"❌ Неверно. Правильный ответ: {correct_answer}"
    
    if explanation:
        response += f"\n\n💡 {explanation}"
    
    await query.edit_message_text(response)
    
    # Следующий вопрос
    context.user_data["current_question"] += 1
    await ask_question(update, context)

# Обновление счета
def update_user_score(user_id, score):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET score = score + ? WHERE user_id = ?", (score, user_id))
    cursor.execute("SELECT score FROM users WHERE user_id = ?", (user_id,))
    new_score = cursor.fetchone()[0]
    level = new_score // 100
    cursor.execute("UPDATE users SET level = ? WHERE user_id = ?", (level, user_id))
    conn.commit()
    conn.close()

# Команда /roulette
async def roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT score FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if not result or result[0] < 10:
        await update.message.reply_text("❌ У вас недостаточно баллов (минимум 10)")
        return

    context.user_data["current_score"] = result[0]

    keyboard = [
        [InlineKeyboardButton("Поставить всё", callback_data="all")],
        [InlineKeyboardButton("Своя ставка", callback_data="custom")],
    ]
    await update.message.reply_text(
        "🎰 Выберите ставку:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Обработка кнопок рулетки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    choice = query.data

    if choice.startswith("ans_"):
        await handle_answer(update, context)
        return
    elif choice.startswith("dir_"):
        await handle_direction(update, context)
        return
    elif choice.startswith("topic_"):
        await handle_topic(update, context)
        return

    current_score = context.user_data.get("current_score", 0)

    if choice == "all":
        bet = current_score
    elif choice == "custom":
        await query.message.reply_text("💰 Введите свою ставку (минимум 10):")
        context.user_data["awaiting_bet"] = True
        return

    if bet < 10:
        await query.message.reply_text("❌ Минимальная ставка - 10 баллов")
        return

    multiplier = random.choice(roulette_multipliers)
    new_score = current_score - bet + int(bet * multiplier)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET score = ? WHERE user_id = ?", (new_score, user_id))
    conn.commit()
    conn.close()

    await query.message.reply_text(
        f"🎰 Результат: {multiplier}x\n"
        f"💵 Новый баланс: {new_score}"
    )

# Обработка текстовой ставки
async def handle_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_bet", False):
        return

    try:
        bet = int(update.message.text)
    except ValueError:
        await update.message.reply_text("🔢 Введите число")
        return

    current_score = context.user_data.get("current_score", 0)
    if bet < 10 or bet > current_score:
        await update.message.reply_text(f"❌ Ставка должна быть от 10 до {current_score}")
        return

    context.user_data["awaiting_bet"] = False
    multiplier = random.choice(roulette_multipliers)
    new_score = current_score - bet + int(bet * multiplier)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET score = ? WHERE user_id = ?", (new_score, update.message.from_user.id))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"🎰 Результат: {multiplier}x\n"
        f"💵 Новый баланс: {new_score}"
    )

# Команда /score
async def score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT score, level FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        await update.message.reply_text(f"📊 Ваш счет: {result[0]}\n📈 Уровень: {result[1]}")
    else:
        await update.message.reply_text("ℹ️ Сначала запустите /start")

# Основная функция
def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Регистрация обработчиков команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("roulette", roulette))
    app.add_handler(CommandHandler("score", score))
    
    # Обработчики callback-запросов
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчик текстовых сообщений (для ставок)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bet))
    
    app.run_polling()

if __name__ == "__main__":
    main()

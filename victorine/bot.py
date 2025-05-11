import sqlite3
import random
import logging
import os
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
QUESTIONS_PATH = os.path.join(BASE_DIR, "questions.txt")

# Настройка логов
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Токен вашего бота (замените на свой)
TOKEN = "7840043878:AAGdk0KsQGubiOxSRMh_UphOOUrqMiDbutU"

# Множители для рулетки
roulette_multipliers = [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1, 1.1, 1.25, 1.5, 1.75, 2, 3, 10]

# Загрузка вопросов
def load_questions():
    try:
        with open(QUESTIONS_PATH, "r", encoding="utf-8") as file:
            lines = [line.strip() for line in file if line.strip()]
        
        questions = []
        for line in lines:
            if "|" in line and line.count("/") >= 3:
                question_part, answers_part = line.split("|", 1)
                parts = [p.strip() for p in answers_part.split("/", 3)]
                if len(parts) == 4:
                    questions.append({
                        "question": question_part.strip(),
                        "correct": parts[0],
                        "wrong": parts[1:4]
                    })
        
        logger.info(f"Загружено {len(questions)} вопросов.")
        return questions
    
    except Exception as e:
        logger.error(f"Ошибка при загрузке вопросов: {e}")
        return []

quiz_questions = load_questions()

# Проверка наличия вопросов
if len(quiz_questions) < 1:
    logger.error("Не найдено вопросов в файле questions.txt")
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

    await update.message.reply_text(
        "🎉 Добро пожаловать в викторину!\n\n"
        "Доступные команды:\n"
        "/quiz - начать викторину\n"
        "/roulette - игра в рулетку\n"
        "/score - ваш текущий счет\n\n"
        "Формат вопросов: вопрос|правильный/неправильный1/неправильный2/неправильный3"
    )

# Команда /quiz
async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    # Выбираем 5 случайных вопросов
    selected_questions = random.sample(quiz_questions, min(5, len(quiz_questions)))
    context.user_data["questions"] = selected_questions
    context.user_data["current_question"] = 0
    context.user_data["score"] = 0

    await ask_question(update, context)

# Задать вопрос с кнопками
async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    questions = context.user_data["questions"]
    current_idx = context.user_data["current_question"]
    
    if current_idx >= len(questions):
        final_score = context.user_data["score"]
        await update.message.reply_text(f"🏆 Викторина завершена! Ваш счет: {final_score}")
        update_user_score(update.message.from_user.id, final_score)
        return

    q_data = questions[current_idx]
    question = q_data["question"]
    correct = q_data["correct"]
    all_answers = [correct] + q_data["wrong"]
    
    # Перемешиваем ответы
    random.shuffle(all_answers)
    
    # Сохраняем индекс правильного ответа
    context.user_data["correct_index"] = all_answers.index(correct)
    
    # Создаем кнопки
    keyboard = [
        [InlineKeyboardButton(answer, callback_data=f"ans_{i}")]
        for i, answer in enumerate(all_answers)
    ]
    
    await update.message.reply_text(
        f"❓ Вопрос {current_idx + 1}/{len(questions)}:\n\n{question}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Обработка ответа
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_choice = int(query.data.split("_")[1])
    correct_idx = context.user_data["correct_index"]
    
    if user_choice == correct_idx:
        context.user_data["score"] += 10
        await query.edit_message_text("✅ Правильно! +10 баллов")
    else:
        correct_answer = query.message.reply_markup.inline_keyboard[correct_idx][0].text
        await query.edit_message_text(f"❌ Неверно. Правильный ответ: {correct_answer}")
    
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
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("roulette", roulette))
    app.add_handler(CommandHandler("score", score))
    
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(all|custom|ans_)"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bet))
    
    app.run_polling()

if __name__ == "__main__":
    main()
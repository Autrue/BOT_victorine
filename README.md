# 📚 Викторинный Бот для Telegram

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot%20API-20.0%2B-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

Многофункциональный бот для проведения викторин с системой баллов, уровнями и мини-игрой "Рулетка". Поддерживает категории вопросов и динамическую загрузку тестов из JSON-файла.

## 🌟 Особенности

- 🎯 **Разнообразные категории** (программирование, наука, география и др.)
- 📊 **Система баллов и уровней**
- 🎰 **Мини-игра "Рулетка"** с различными множителями
- 📝 **Динамическая загрузка вопросов** из JSON-файла
- 💡 **Объяснения правильных ответов**
- 🏆 **Топ игроков** (в разработке)

## 🛠 Технологии

- Python 3.8+
- python-telegram-bot 20.0+
- SQLite3 (хранение данных пользователей)
- JSON (хранение вопросов)

## ⚙️ Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/ваш-репозиторий.git
cd quiz-bot
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл конфигурации:
```bash
cp config.example.py config.py
```

4. Замените `YOUR_TELEGRAM_BOT_TOKEN` в `config.py` на токен от [@BotFather](https://t.me/BotFather)

## 📂 Структура проекта

```
quiz-bot/
├── bot.py                # Основной код бота
├── quiz_data.json        # Вопросы и ответы в JSON-формате
├── database.db           # База данных SQLite (создается автоматически)
├── config.py             # Конфигурация (токен бота)
├── requirements.txt      # Зависимости
└── logs/
    └── bot.log           # Логи работы бота
```

## 📝 Формат вопросов (quiz_data.json)

Пример структуры JSON-файла:
```json
{
  "directions": {
    "programming": {
      "name": "Программирование",
      "topics": {
        "python": {
          "name": "Python",
          "quizzes": [
            {
              "id": 1,
              "questions": [
                {
                  "question": "Что такое Python?",
                  "answers": ["Язык разметки", "Язык программирования", "База данных", "Фреймворк"],
                  "correct_answer": 1,
                  "explanation": "Python - интерпретируемый язык программирования высокого уровня"
                }
              ]
            }
          ]
        }
      }
    }
  }
}
```

## 🎮 Команды бота

- `/start` - Начало работы с ботом
- `/roulette` - Игра в рулетку (ставка от 10 баллов)
- `/score` - Показать текущий счет и уровень
- `/top` - Топ игроков (в разработке)

## 🚀 Запуск

```bash
python bot.py
```

Для постоянной работы используйте:
```bash
nohup python bot.py &
```

## 📈 Планы развития

- [ ] Добавить систему достижений
- [ ] Реализовать мультиязычную поддержку
- [ ] Добавить изображения к вопросам
- [ ] Разработать веб-панель управления вопросами

## 🤝 Как помочь проекту

1. Форкните репозиторий
2. Создайте ветку с вашими изменениями (`git checkout -b feature/AmazingFeature`)
3. Зафиксируйте изменения (`git commit -m 'Add some AmazingFeature'`)
4. Запушьте изменения (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📜 Лицензия

MIT License. Подробнее см. в файле [LICENSE](LICENSE).

---

**Автор**: Артур  
**Контакты**: [artursmorz@gmail.com]  
**Версия**: 1.0.0

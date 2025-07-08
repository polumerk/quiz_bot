# Настройка команд Quiz Bot

## 📋 Обзор

Quiz Bot поддерживает 8 команд, которые отображаются в меню Telegram:

### 🇷🇺 Команды (русский язык)
- `/start` - 🎮 Начать новую игру или настроить параметры
- `/next` - ⏭️ Перейти к следующему раунду
- `/stat` - 📊 Показать статистику игр и игроков
- `/lang` - 🌍 Сменить язык интерфейса (русский/английский)
- `/news` - 📰 Новости и обновления бота
- `/exit` - 👋 Завершить текущую игру
- `/stop` - 🛑 Остановить игру
- `/debug` - 🐛 Переключить режим отладки

### 🇬🇧 Commands (English)
- `/start` - 🎮 Start new game or configure settings
- `/next` - ⏭️ Go to next round
- `/stat` - 📊 Show game and player statistics
- `/lang` - 🌍 Change interface language (Russian/English)
- `/news` - 📰 Bot news and updates
- `/exit` - 👋 End current game
- `/stop` - 🛑 Stop game
- `/debug` - 🐛 Toggle debug mode

## 🔧 Способы регистрации команд

### 1. Автоматическая регистрация (рекомендуется)

Команды автоматически регистрируются при запуске бота через `main.py`. Это происходит в функции `run_bot()`:

```python
# Register bot commands (menu in Telegram)
logging.info("Registering bot commands...")
try:
    # Commands as tuples (command, description)
    commands_ru = [
        ("start", "🎮 Начать новую игру или настроить параметры"),
        # ... остальные команды
    ]
    
    # Register commands for Russian users (default)
    await app.bot.set_my_commands(commands_ru)
    
    # Register commands for English users
    await app.bot.set_my_commands(commands_en, language_code="en")
    
except Exception as e:
    logging.warning(f"⚠️ Could not register bot commands: {e}")
```

### 2. Ручная регистрация

Для ручной регистрации команд используйте скрипт `quick_register_commands.py`:

```bash
python quick_register_commands.py
```

**Возможности скрипта:**
1. **Регистрация команд** - устанавливает все команды в Telegram
2. **Просмотр команд** - показывает текущие зарегистрированные команды
3. **Очистка команд** - удаляет все команды из меню

## 🔑 Настройка токена

### Вариант 1: Переменная окружения
```bash
# Windows PowerShell
$env:TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"

# Linux/macOS
export TELEGRAM_TOKEN="YOUR_BOT_TOKEN"
```

### Вариант 2: Replit Secrets
1. Откройте вкладку "Secrets" в Replit
2. Добавьте новый секрет:
   - Ключ: `TELEGRAM_TOKEN`
   - Значение: ваш токен от @BotFather

### Вариант 3: Ручной ввод
Если токен не найден, скрипт попросит ввести его вручную.

## ✅ Проверка результата

После регистрации команд:

1. **Откройте чат с ботом в Telegram**
2. **Нажмите кнопку "Меню" (☰) или введите "/"**
3. **Должны появиться все зарегистрированные команды**

> ⏰ **Внимание**: Команды могут появиться в меню через 1-5 минут после регистрации.

## 🛠️ Техническая информация

### API методы
- `set_my_commands()` - устанавливает команды
- `get_my_commands()` - получает текущие команды
- `delete_my_commands()` - удаляет все команды

### Поддержка языков
Команды регистрируются для двух языков:
- **По умолчанию**: русский язык
- **Английский**: `language_code="en"`

### Формат команд
Команды передаются как список кортежей:
```python
[
    ("command_name", "Command description"),
    ("start", "🎮 Start new game"),
    # ...
]
```

## 🐛 Устранение проблем

### Команды не появляются в меню
1. Подождите 5-10 минут
2. Перезапустите Telegram
3. Проверьте токен бота
4. Убедитесь, что бот не заблокирован

### Ошибки при регистрации
- **Invalid token**: проверьте токен от @BotFather
- **Network error**: проверьте интернет-соединение
- **Rate limit**: подождите и попробуйте снова

### Логи
Проверьте логи бота при запуске:
```
✅ Bot commands registered for Russian language
✅ Bot commands registered for English language
📋 Registered 8 bot commands
```

## 📚 Дополнительные ресурсы

- [Telegram Bot API - setMyCommands](https://core.telegram.org/bots/api#setmycommands)
- [Telegram Bot API - BotCommand](https://core.telegram.org/bots/api#botcommand)
- [Создание бота через @BotFather](https://core.telegram.org/bots#creating-a-new-bot) 
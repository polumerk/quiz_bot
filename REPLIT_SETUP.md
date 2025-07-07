# 🚀 Настройка Quiz Bot в Replit

## 📋 Быстрый старт

### 1. 🔑 Настройка API ключей

#### Telegram Bot Token:
1. Создайте бота через [@BotFather](https://t.me/botfather)
2. Получите токен бота
3. В Replit откройте **Secrets** (🔒 значок в левой панели)
4. Добавьте новый секрет:
   - **Key:** `TELEGRAM_TOKEN`
   - **Value:** ваш токен бота (например: `1234567890:AABBCCddEEfF...`)

#### OpenAI API Key:
1. Получите API ключ на [platform.openai.com](https://platform.openai.com/api-keys)
2. В Replit Secrets добавьте:
   - **Key:** `OPENAI_API_KEY`
   - **Value:** ваш OpenAI ключ (например: `sk-proj-abc123...`)

### 2. 🔧 Переменные окружения (опционально)

В Replit Secrets можно также настроить:

```
# Основные настройки
TELEGRAM_TOKEN=ваш_токен_бота
OPENAI_API_KEY=ваш_openai_ключ

# Дополнительные настройки (опционально)
WEBHOOK_URL=https://ваш-replit-url.replit.dev
LOG_LEVEL=INFO
```

### 3. 📦 Установка зависимостей (если нужно)

Если при запуске есть ошибки с зависимостями, выполните в Shell:
```bash
python install_deps.py
```

Или вручную:
```bash
pip install -r requirements.txt
```

### 4. 🎮 Запуск бота

1. Нажмите **Run** в Replit
2. Бот автоматически определит Replit окружение
3. Перейдите к вашему боту в Telegram
4. Отправьте `/start`

## 🔧 Настройка Secrets в Replit

### Шаг за шагом:

1. **Откройте ваш Replit проект**
2. **Найдите значок замка (🔒) в левой панели** - это "Secrets"
3. **Нажмите "New Secret"**
4. **Добавьте TELEGRAM_TOKEN:**
   - Key: `TELEGRAM_TOKEN`
   - Value: `1234567890:AABBCCddEEfF...` (ваш токен)
5. **Добавьте OPENAI_API_KEY:**
   - Key: `OPENAI_API_KEY`  
   - Value: `sk-proj-abc123...` (ваш ключ)

### 💡 Почему Secrets?

- ✅ **Безопасность:** ключи не попадают в код
- ✅ **Приватность:** доступны только вам
- ✅ **Удобство:** автоматически загружаются как переменные окружения

## 🐛 Диагностика проблем

### Проверка настроек:
```python
import os
print("TELEGRAM_TOKEN:", "✅ Настроен" if os.getenv('TELEGRAM_TOKEN') else "❌ Не найден")  
print("OPENAI_API_KEY:", "✅ Настроен" if os.getenv('OPENAI_API_KEY') else "❌ Не найден")
```

### Типичные ошибки:

1. **"OpenAI API ключ не настроен"**
   - Проверьте правильность имени: `OPENAI_API_KEY`
   - Убедитесь что ключ начинается с `sk-`

2. **"Invalid token"**  
   - Проверьте `TELEGRAM_TOKEN`
   - Убедитесь что токен правильный

3. **"Webhook failed"**
   - Нормально! Бот переключится на polling
   - Всё будет работать

4. **"No JobQueue set up"**
   - Установите зависимости: `python install_deps.py`
   - Или: `pip install "python-telegram-bot[job-queue]"`
   - Без этого нет таймаутов вопросов (не критично)

## 🎯 Готово!

После настройки Secrets ваш бот готов к работе! Все API ключи будут загружаться автоматически и безопасно.

**Важно:** Никогда не добавляйте API ключи в код - только через Replit Secrets! 🔐
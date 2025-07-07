# 🚀 Руководство по запуску Quiz Bot на Replit

## 🎯 Проблема
Replit имеет особенности с event loops, которые могут вызывать ошибки при запуске бота.

## 📋 Доступные методы запуска

### 🥇 **Метод 1: Основной (рекомендуемый)**
```bash
python main.py
```

**Ожидаемый результат:** Webhook → Polling fallback  
**Состояние:** ✅ Исправлен в последней версии

---

### 🥈 **Метод 2: Replit-специфичный**
```bash
python main_replit.py
```

**Когда использовать:** Если main.py выдает event loop ошибки  
**Особенности:** Применяет nest_asyncio перед запуском

---

### 🥉 **Метод 3: Только Polling (самый надежный)**
```bash
python main_polling_only.py
```

**Когда использовать:** Если webhook не работает в принципе  
**Особенности:** 
- Полностью отключает webhook
- Использует только polling режим
- Максимальная совместимость

## 🔧 Пошаговое решение проблем

### Шаг 1: Обновите код
```bash
git pull origin cursor/study-the-project-6342
```

### Шаг 2: Попробуйте методы по порядку

#### Попытка 1:
```bash
python main.py
```

**Ожидаемые логи (успех):**
```
✅ Webhook set successfully
🌐 Starting webhook server on 0.0.0.0:443
```

**Или (успешный fallback):**
```
❌ Webhook server failed: ...
📡 Starting polling with fresh application...
```

#### Если не работает → Попытка 2:
```bash
python main_replit.py
```

#### Если не работает → Попытка 3:
```bash
python main_polling_only.py
```

**Ожидаемые логи:**
```
=== QUIZ BOT STARTING (POLLING ONLY) ===
🧹 Clearing any existing webhooks...
📡 Starting polling mode (webhook disabled)...
```

## 🐛 Диагностика проблем

### Запустите отладочный скрипт:
```bash
python debug_replit.py
```

Это покажет доступные переменные окружения и поможет в диагностике.

## 📊 Сравнение методов

| Метод | Webhook | Polling | Event Loop | Надежность |
|-------|---------|---------|------------|------------|
| `main.py` | ✅ → 🔄 | ✅ | 🔧 Исправлен | ⭐⭐⭐⭐⭐ |
| `main_replit.py` | ✅ → 🔄 | ✅ | ✅ nest_asyncio | ⭐⭐⭐⭐ |
| `main_polling_only.py` | ❌ | ✅ | ✅ | ⭐⭐⭐⭐⭐ |

## ✅ Критерии успеха

Бот работает правильно, если видите:
```
📡 Starting polling mode...
# Или
🌐 Starting webhook server...
```

И НЕ видите:
```
❌ Fatal error: Cannot close a running event loop
❌ All methods failed: ...
```

## 🆘 Если ничего не помогает

1. **Проверьте зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Проверьте переменные окружения:**
   ```bash
   echo $REPLIT_DEV_DOMAIN
   echo $REPL_SLUG
   ```

3. **Сообщите о проблеме** с полными логами запуска

## 🎉 Заключение

В 99% случаев один из трех методов сработает. Начните с `main.py`, переходите к `main_polling_only.py` если есть проблемы.

**Polling режим работает везде и всегда!** 📡
# 🚀 **СИСТЕМА АВТОМАТИЧЕСКОГО ВЫБОРА РЕЖИМА РАЗВЕРТЫВАНИЯ**

## 🎯 **ОПИСАНИЕ**
Система автоматически выбирает между webhook и polling режимами на основе переменных окружения и конфигурации.

## 🔧 **ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ**

### **`DEPLOYMENT_MODE`**
Основная переменная для управления режимом развертывания:

| Значение | Описание | Поведение |
|----------|----------|-----------|
| `auto` | **По умолчанию** | Автоматический выбор на основе конфигурации |
| `webhook` | Принудительный webhook | Всегда пытается использовать webhook |
| `polling` | Принудительный polling | Всегда использует polling |

### **`WEBHOOK_URL`**
URL для webhook (только для webhook режима):
```
WEBHOOK_URL=https://your-domain.com
```

### **`WEBHOOK_PORT`**
Порт для webhook (по умолчанию: 443):
```
WEBHOOK_PORT=8443
```

## 🎮 **РЕЖИМЫ РАБОТЫ**

### **1. 🤖 AUTO MODE (Рекомендуется)**
```bash
# Не указывать DEPLOYMENT_MODE или:
DEPLOYMENT_MODE=auto
```

**Логика выбора:**
- ✅ Если `WEBHOOK_URL` настроен → webhook
- ✅ Если Replit окружение с доступным URL → webhook  
- ✅ Иначе → polling (безопасный выбор)

### **2. 🌐 WEBHOOK MODE**
```bash
DEPLOYMENT_MODE=webhook
WEBHOOK_URL=https://your-domain.com
WEBHOOK_PORT=443
```

**Принудительно использует webhook** (даже если URL не настроен)

### **3. 📡 POLLING MODE**
```bash
DEPLOYMENT_MODE=polling
```

**Принудительно использует polling** (игнорирует webhook настройки)

## 🌍 **ПРИМЕРЫ НАСТРОЙКИ**

### **Local Development**
```bash
# .env file
DEPLOYMENT_MODE=polling
TELEGRAM_TOKEN=your_token
OPENAI_API_KEY=your_key
```

### **Replit Deployment**
```bash
# Replit Secrets
DEPLOYMENT_MODE=auto
TELEGRAM_TOKEN=your_token
OPENAI_API_KEY=your_key
# WEBHOOK_URL автоматически определится из REPLIT_URL
```

### **VPS/Dedicated Server**
```bash
# .env file
DEPLOYMENT_MODE=auto
WEBHOOK_URL=https://your-domain.com
WEBHOOK_PORT=443
TELEGRAM_TOKEN=your_token
OPENAI_API_KEY=your_key
```

### **Heroku/Railway/etc**
```bash
# Environment variables
DEPLOYMENT_MODE=webhook
WEBHOOK_URL=https://your-app.herokuapp.com
TELEGRAM_TOKEN=your_token
OPENAI_API_KEY=your_key
```

## 📊 **ЛОГИРОВАНИЕ**

При запуске бот покажет выбранный режим:

```
🚀 Deployment mode: 📡 Polling mode (explicit)
🚀 Deployment mode: 🌐 Webhook mode (auto-detected: https://example.com)
🚀 Deployment mode: 📡 Polling mode (auto-detected, no webhook URL)
```

## 🔄 **MIGRATION GUIDE**

### **Из старой системы:**
```python
# СТАРЫЙ СПОСОБ (удален)
FORCE_POLLING = True

# НОВЫЙ СПОСОБ
DEPLOYMENT_MODE = "polling"  # или "auto", "webhook"
```

### **Replit Secrets:**
```
# Удалить (если есть):
FORCE_POLLING

# Добавить:
DEPLOYMENT_MODE = auto
```

## 🛠️ **TROUBLESHOOTING**

### **Проблема:** Webhook не работает
**Решение:** 
```bash
# Принудительно переключиться на polling
DEPLOYMENT_MODE=polling
```

### **Проблема:** Нужен webhook на локальной машине
**Решение:**
```bash
# Использовать ngrok для HTTPS tunnel
DEPLOYMENT_MODE=webhook
WEBHOOK_URL=https://abc123.ngrok.io
```

### **Проблема:** Неизвестный режим
**Решение:**
```bash
# Система автоматически перейдет на polling
# Проверить spelling в DEPLOYMENT_MODE
```

## ✅ **ПРЕИМУЩЕСТВА НОВОЙ СИСТЕМЫ**

1. **🔄 Автоматический выбор** - не нужно вручную переключать режимы
2. **🛡️ Безопасность** - polling по умолчанию при неопределенности
3. **📈 Гибкость** - легко переключать через переменные окружения
4. **🌍 Универсальность** - работает в любом окружении
5. **📊 Прозрачность** - четкое логирование выбранного режима

## 📋 **SUMMARY**

| Сценарий | Переменная | Результат |
|----------|------------|-----------|
| **Development** | `DEPLOYMENT_MODE=polling` | 📡 Polling |
| **Replit** | `DEPLOYMENT_MODE=auto` | 🌐 Webhook (если URL доступен) |
| **Production** | `DEPLOYMENT_MODE=webhook` | 🌐 Webhook |
| **По умолчанию** | *(не указано)* | 📡 Polling |

**🎯 Система умная, безопасная и гибкая!**
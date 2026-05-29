# SmartSkyBot 🌤

Персональный погодный помощник в Telegram. Рекомендации с учётом профиля пользователя.

## Возможности

- 🌤 Погода в любом городе мира  
- 👤 6 профилей: Строитель, Водитель, Родитель, Дачник, Рыбак, Обычный  
- 📋 Персональные советы по погоде для каждого профиля  
- 🏙 Смена города  

## Установка

```bash
git clone https://github.com/Born3Life/smart-sky-bot.git
cd smart-sky-bot
uv venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate # Linux/Mac
uv sync
```

## Настройка

Скопируй `.env.example` → `.env` и заполни:

```env
BOT_TOKEN=токен_от_BotFather
OPENWEATHER_API_KEY=ключ_OpenWeather
```

Получить ключи:
- Бот: @BotFather  
- OpenWeather: https://openweathermap.org/api  

## Запуск

```bash
python bot.py
```

## Деплой на Render

1. Залить код на GitHub  
2. Render → New Web Service → подключить репозиторий  
3. **Build**: `pip install -r requirements.txt`  
4. **Start**: `python -m bot`  
5. **Env**: BOT_TOKEN, OPENWEATHER_API_KEY  

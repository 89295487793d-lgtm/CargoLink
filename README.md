# CargoLink — стартовый MVP

Telegram-бот, FastAPI и мобильная стартовая страница Mini App. Это рабочая основа проекта, но не законченная production-платформа.

## Подготовка окружения

1. Создайте Telegram-бота через [@BotFather](https://t.me/BotFather) и скопируйте токен.
2. Если файла `.env` ещё нет, выполните `cp .env.example .env`.
3. В `.env` задайте `BOT_TOKEN`. Не вставляйте токен в исходный код и не отправляйте его в чат.
4. При необходимости измените `POSTGRES_PASSWORD`. Используйте буквенно-цифровой пароль без символов URL-разметки.
5. Для кнопки открытия Mini App укажите публичный HTTPS-адрес в `WEBAPP_URL`. Без него бот работает в режиме Telegram-меню.

## Запуск через Docker Compose

Из корня репозитория:

```bash
cp .env.example .env
# Откройте .env и вставьте BOT_TOKEN
docker compose config
docker compose up --build -d
docker compose ps
```

Проверка API и PostgreSQL:

```bash
curl -fsS http://localhost:8000/health
docker compose logs --tail=100 db init-db api bot
```

В health endpoint должны вернуться `"status":"ok"` и `"database":"ok"`. Затем отправьте боту `/start` в Telegram.

Логи только бота:

```bash
docker compose logs -f bot
```

Перезапуск бота после изменения настроек:

```bash
docker compose up -d --build bot
```

Остановка: `docker compose down`. Данные PostgreSQL сохраняются в Docker volume. Для полного удаления локальной базы используйте `docker compose down -v` — это удалит данные.

## Запуск в Codespaces без Docker

Codespaces должен иметь Docker Compose. В терминале выполните те же команды из корня репозитория. Если запускаете Python-процесс напрямую, сначала поднимите PostgreSQL и установите зависимости:

```bash
python -m pip install -r requirements.txt
python -m app.init_db
python -m app.bot_main
```

При прямом запуске задайте `DATABASE_URL` с адресом доступной PostgreSQL. Значение `db` работает внутри Docker Compose, но не является адресом PostgreSQL на хосте Codespaces.

## Что сейчас реализовано

- Telegram `/start`, главное меню и первичная регистрация.
- Сохранение ФИО и номера телефона пользователя в PostgreSQL; номер не публикуется.
- Проверка соединения с PostgreSQL перед запуском long polling.
- Проверка Telegram-токена при подключении к Bot API и понятное сообщение при отсутствии токена.
- FastAPI health-check с реальной проверкой PostgreSQL.
- Мобильная стартовая страница с заглушками разделов.
- GitHub Actions проверяет компиляцию Python, Docker-сборку, PostgreSQL, инициализацию схемы, health endpoint и импорт модуля бота.

## Пока не реализовано

Публикация и поиск грузов, ставки перевозчиков, полноценный каталог автомобилей, внутренний чат, взаимное раскрытие контактов, модерация, миграции Alembic и production hardening.

Не размещайте сервис публично с реальными персональными данными до настройки аутентификации и авторизации, миграций, резервного копирования, мониторинга, ограничения доступа и проверки требований к персональным данным.

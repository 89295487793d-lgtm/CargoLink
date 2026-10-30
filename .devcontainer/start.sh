#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

echo "==> Подготовка CargoLink"
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Создан .env из .env.example"
fi

echo "==> Запуск базы данных и API"
docker compose up -d --build db init-db api

echo "==> Проверка API"
for attempt in $(seq 1 30); do
  if curl --fail --silent http://localhost:8000/health >/dev/null; then
    echo "CargoLink API работает: http://localhost:8000"
    break
  fi
  if [[ "$attempt" -eq 30 ]]; then
    echo "API не ответил. Последние логи:"
    docker compose logs --tail=80 api db
    exit 1
  fi
  sleep 2
done

TOKEN="$(grep -E '^BOT_TOKEN=' .env | cut -d= -f2- || true)"
if [[ -n "$TOKEN" && "$TOKEN" != "PASTE_TELEGRAM_BOT_TOKEN_HERE" ]]; then
  echo "==> Найден BOT_TOKEN, запускаю Telegram-бота"
  docker compose up -d --build bot
  docker compose ps
  echo "Логи бота: docker compose logs -f bot"
else
  echo
  echo "API и база запущены. Telegram-бот ожидает токен."
  echo "Добавь BOT_TOKEN в .env, затем выполни: docker compose up -d --build bot"
  docker compose ps
fi

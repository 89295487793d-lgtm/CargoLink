# CargoLink 2.0 — техническая архитектура

## Зафиксированные параметры
- Основной приоритет: опасные жидкие грузы (liquid).
- Второе полноценное направление: обычные грузы.
- Транспорт: road, автомобильный.
- География: CIS, страны СНГ.
- Текущие утверждённые экраны и структура формы не меняются без отдельного согласования.

## Архитектура
Модульный монолит: Telegram Mini App и Bot → FastAPI → доменные сервисы → PostgreSQL через SQLAlchemy. Alembic применяется для версионирования схемы. Не дробим MVP на микросервисы до появления подтверждённой нагрузки.

Домены: Identity & Companies, Marketplace, Dangerous Goods, Fleet, Compatibility, Shipments, Documents & Finance, Analytics, Geography.

## Модель данных
Существующие таблицы сохраняются: users, cargo_requests, carrier_offers, cargo_chats, cargo_chat_messages, cargo_status_events.

Новые сущности ядра: companies, company_members, dangerous_goods, vehicles, tank_specs, drivers, compliance_documents, compatibility_checks, shipments.

Следующие сущности: cargo_catalog, cargo_requirements, cargo_compatibility_rules, vehicle_capabilities, driver_certificates, shipment_events, shipment_documents, payments, ratings, audit_logs, countries, regions, cities, border_crossings, route_restrictions.

UN number хранится строкой из четырёх цифр. Классификация опасного груза отделена от заявки. Источник и версия нормативных данных фиксируются. Вес, объём, даты, валюта и страны должны иметь однозначные единицы и стандарты (ISO 3166-1 alpha-2, ISO 4217). Для договора/перевозки сохраняется снимок критичных параметров на момент сделки.

## Совместимость
Результат проверки: eligible, blocked или manual_review. Сначала проверяются обязательные условия (продукт разрешён для цистерны, вместимость, оборудование, документы, маршрут и нормы применимых стран), только после этого можно ранжировать транспорт по цене и расстоянию. Проверка предварительная, не является юридической сертификацией. Нормативные правила должны проходить экспертную проверку по каждой стране и версии.

## API v2
- GET /api/v2/cargo/dangerous-goods?q=&limit=
- GET /api/v2/cargo/dangerous-goods/{un_number}
- POST /api/v2/compatibility/check

Следующие группы: requests, companies, vehicles, drivers, documents, offers, shipments, finance, analytics. Все write-операции должны проверять Telegram initData, RBAC, ownership, idempotency для финансовых и статусных операций, вести аудит и ограничивать частоту запросов.

## Внедрение
1. Фундамент БД и миграции.
2. Каталог опасных жидких грузов с проверенными источниками.
3. Автоцистерны и транспорт.
4. Compatibility engine.
5. Компании, роли, водители и документы.
6. Обычные грузы.
7. Перевозки, финансы и аналитика.
8. География CIS, национальные нормы, валюты и транзит.

## Совместимость и эксплуатация
Старые API и workflow сохраняются до контролируемого перехода. Перед production миграцией — резервная копия и тест на копии базы. Документы хранятся в защищённом хранилище, в БД — только storage key и метаданные.

## Текущий статус
Добавлен первый каркас доменных моделей, поиск жидких опасных грузов, endpoint предварительной проверки совместимости и unit tests базовых сценариев. Это не готовый справочник и не завершённая нормативная система. Реальные перевозки нельзя допускать на основании непроверенных записей.

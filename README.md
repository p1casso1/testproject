# Developer Landing Backend

Бэкенд-сервис для лендинг-презентации разработчика: REST API для формы обратной связи
с валидацией, email-уведомлениями, AI-анализом обращений, rate limiting'ом и
файловым хранением логов/метрик.

> Тестовое задание (Backend-ориентированно). Стек: **Python 3.11 + FastAPI**.

---

## Содержание

1. [Как запустить проект](#1-как-запустить-проект)
2. [Стек технологий](#2-стек-технологий)
3. [Архитектура](#3-архитектура)
4. [Реализация API](#4-реализация-api)
5. [AI-интеграция](#5-ai-интеграция)
6. [Что сделано с помощью AI](#6-что-сделано-с-помощью-ai)
7. [Хранение данных](#7-хранение-данных)
8. [Деплой](#8-деплой)

---

## 1. Как запустить проект

### Требования
- Python 3.9+ (разработано и протестировано на 3.11)
- pip

### Установка и запуск (локально)

```bash
# 1. Клонировать репозиторий и перейти в папку
git clone <repo_url>
cd <repo_folder>

# 2. Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Настроить переменные окружения
cp .env.example .env
# отредактируйте .env: SMTP-данные и ANTHROPIC_API_KEY (опционально, см. ниже)

# 5. Запустить сервер
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Сервис будет доступен на `http://localhost:8000`:
- `http://localhost:8000/docs` — Swagger UI
- `http://localhost:8000/redoc` — ReDoc
- `http://localhost:8000/static/index.html` — демо-фронтенд (форма обратной связи)
- `http://localhost:8000/api/health` — health check

### Запуск через Docker

```bash
docker build -t dev-landing-backend .
docker run -p 8000:8000 --env-file .env dev-landing-backend
```

### Важно: сервис работает даже без настройки SMTP и AI

Если переменные `SMTP_*` или `ANTHROPIC_API_KEY` не заданы — сервис **не упадёт**.
AI-анализ переключится на rule-based fallback, а email-уведомления просто не будут
отправлены (это залогируется), но API всё равно вернёт корректный успешный ответ.
Так что для быстрой проверки можно вообще не трогать `.env` и сразу запускать сервис.

### Переменные окружения (`.env`)

| Переменная | Описание | Обязательна |
|---|---|---|
| `ANTHROPIC_API_KEY` | Ключ Anthropic API для AI-анализа | Нет (есть fallback) |
| `ANTHROPIC_MODEL` | Модель Claude (по умолчанию `claude-3-5-haiku-20241022`) | Нет |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | Данные для отправки писем | Нет (есть fallback) |
| `OWNER_EMAIL` | Куда слать письмо владельцу сайта | Нет |
| `CORS_ORIGINS` | Список разрешённых origin через запятую | Нет |
| `RATE_LIMIT_MAX_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` | Параметры rate limiting | Нет (есть дефолты) |

Полный список — в [`.env.example`](.env.example).

---

## 2. Стек технологий

**Backend:**
- Python 3.11
- FastAPI — веб-фреймворк, REST API, авто-генерация OpenAPI/Swagger
- Pydantic v2 / pydantic-settings — валидация данных и конфигурация
- Uvicorn — ASGI-сервер

**AI:**
- Anthropic API (`anthropic` Python SDK), модель `claude-3-5-haiku-20241022`
- Rule-based fallback на чистом Python (без внешних зависимостей) на случай
  недоступности AI-провайдера

**Email:**
- `smtplib` (стандартная библиотека) — без сторонних SaaS-сервисов, чтобы
  деплой не зависел от платных API рассылки

**Хранение данных:**
- Файловая система (JSON), без БД — согласно условиям задания. Потокобезопасный
  доступ через `threading.Lock` + атомарную запись через временный файл

**Прочее:**
- Docker (опционально, для деплоя)
- Логирование — `logging` + `RotatingFileHandler` (встроенная ротация)

---

## 3. Архитектура

Слоистая архитектура: **Controllers → Services → Repositories**.

```
project/
├── app/
│   ├── main.py                  # точка входа, сборка приложения
│   ├── config.py                # конфигурация (pydantic-settings, .env)
│   ├── api/
│   │   └── routes/
│   │       ├── contact.py       # Controller: POST /api/contact
│   │       ├── health.py        # Controller: GET /api/health
│   │       └── metrics.py       # Controller: GET /api/metrics
│   ├── services/                # Бизнес-логика
│   │   ├── contact_service.py   # оркестрация всего флоу обращения
│   │   ├── ai_service.py        # AI-анализ + fallback
│   │   ├── email_service.py     # отправка email + fallback
│   │   └── rate_limiter.py      # rate limiting
│   ├── repositories/            # Слой доступа к данным (файловое хранилище)
│   │   ├── json_file_repository.py   # базовый потокобезопасный JSON-репозиторий
│   │   ├── contact_repository.py     # история обращений
│   │   ├── metrics_repository.py     # агрегированная статистика
│   │   └── rate_limit_repository.py  # данные rate limiting
│   ├── models/
│   │   └── schemas.py           # Pydantic-схемы запросов/ответов
│   └── core/
│       ├── exceptions.py        # кастомные исключения с HTTP-статусами
│       ├── error_handlers.py    # глобальный обработчик ошибок
│       ├── middleware.py        # логирование запросов + request_id
│       └── logging_config.py    # настройка логгеров
├── frontend/
│   └── index.html               # бонус: демо-страница с формой
├── data/                        # JSON-хранилища (создаются автоматически)
├── logs/                        # лог-файлы (создаются автоматически)
├── requirements.txt
├── .env.example
├── Dockerfile
├── postman_collection.json
├── curl_examples.md
└── README.md
```

### Паттерны проектирования

- **Layered architecture (Controller → Service → Repository)** — чёткое разделение
  ответственности: контроллеры ничего не знают о хранении данных, сервисы не
  работают с HTTP напрямую.
- **Dependency boundary через конструкторы** — каждый сервис/репозиторий получает
  конфигурацию через `get_settings()`, что упрощает тестирование.
- **Graceful degradation / fallback pattern** — и AI, и email-сервис спроектированы
  так, что сбой внешней системы никогда не приводит к падению основного запроса.
- **Repository pattern поверх файлового хранилища** — `JSONFileRepository` инкапсулирует
  чтение/запись/атомарное обновление, конкретные репозитории (`ContactRepository`,
  `MetricsRepository`, `RateLimitRepository`) не знают деталей хранения.
- **Единый формат ошибок** — все исключения (`AppException` и потомки) перехватываются
  глобальным `error_handler`, ошибки FastAPI-валидации тоже приводятся к тому же формату.

### Почему такой выбор технологий

- **FastAPI** — нативная асинхронность (важно для вызова AI API и SMTP без блокировки
  event loop через `asyncio.to_thread`), автоматическая валидация через Pydantic,
  автогенерация Swagger/OpenAPI "из коробки" (требование задания).
- **Файловое хранилище вместо БД** — задание явно говорит, что БД не обязательна;
  решение через JSON-файлы с file-lock и атомарной записью показывает, что можно
  построить надёжное хранилище и без БД, при этом архитектура (репозитории) такая,
  что переход на БД (например, SQLAlchemy + Postgres) потребовал бы переписать
  только слой `repositories/`, не трогая `services/` и `api/`.
- **Anthropic Claude** — выбран как AI-провайдер; модель `claude-3-5-haiku` — быстрая
  и дешёвая модель, достаточная для классификации/тональности коротких сообщений.

---

## 4. Реализация API

### `POST /api/contact`

Принимает форму обратной связи, валидирует, прогоняет через AI, отправляет письма,
сохраняет в хранилище.

**Request:**
```json
{
  "name": "Иван Иванов",
  "phone": "+998901234567",
  "email": "ivan@example.com",
  "comment": "Здравствуйте! Хочу обсудить разработку backend для моего стартапа."
}
```

**Response `200 OK`:**
```json
{
  "success": true,
  "message": "Спасибо! Ваше обращение получено и обрабатывается.",
  "request_id": "1e30ce61-2fa2-450d-a7f0-d0c04950f90e",
  "ai_analysis": {
    "sentiment": "positive",
    "category": "project_inquiry",
    "auto_reply": "Спасибо за обращение! ...",
    "provider": "anthropic",
    "confidence": null
  },
  "owner_email_sent": true,
  "user_email_sent": true,
  "timestamp": "2026-06-20T13:30:37.511931Z"
}
```

**Response `422 Unprocessable Entity`** (ошибка валидации):
```json
{
  "success": false,
  "error": "validation_error",
  "detail": "body.email: value is not a valid email address...",
  "request_id": "...",
  "timestamp": "..."
}
```

**Response `429 Too Many Requests`** (превышен rate limit):
```json
{
  "success": false,
  "error": "rate_limit_exceeded",
  "detail": "Максимум 5 запросов за 60 минут",
  "request_id": "...",
  "timestamp": "..."
}
```

### `GET /api/health`

Проверка статуса сервиса + флаги, настроены ли AI и SMTP.

```json
{
  "status": "ok",
  "timestamp": "...",
  "version": "1.0.0",
  "ai_provider_configured": true,
  "smtp_configured": true
}
```

### `GET /api/metrics`

Агрегированная статистика обращений (хранится в `data/metrics.json`).

```json
{
  "total_requests": 12,
  "successful_requests": 10,
  "failed_requests": 1,
  "rate_limited_requests": 1,
  "sentiment_breakdown": { "positive": 6, "neutral": 3, "negative": 1 },
  "category_breakdown": { "project_inquiry": 5, "question": 3, "job_offer": 2 },
  "last_request_at": "..."
}
```

### Валидация и обработка ошибок

- Валидация на уровне Pydantic-схем (`app/models/schemas.py`): имя (минимум 2 символа,
  должно содержать буквы), телефон (regex на цифры/+/-/скобки/пробелы), email
  (`EmailStr`), комментарий (от 5 до 2000 символов).
- Любая ошибка приводится к единому JSON-формату `ErrorResponse` через глобальный
  обработчик ошибок (`app/core/error_handlers.py`) с подходящим HTTP-статусом:
  `422` — валидация, `429` — rate limit, `502` — сбой внешнего сервиса,
  `500` — непредвиденная ошибка.
- Каждой ошибке присваивается `request_id`, который также присутствует в логах —
  это позволяет быстро найти конкретный запрос в `logs/app.log` / `logs/requests.log`.

### RESTful-принципы

- Существительные во множественном числе не используются избыточно — единственный
  ресурс формы обратной связи: `POST /api/contact`.
- Корректные HTTP-методы (`GET` для чтения, `POST` для создания) и статус-коды
  (`200`, `422`, `429`, `500`, `502`).
- CORS настроен через `CORSMiddleware` с явным списком разрешённых origin
  (берётся из `.env`, см. `CORS_ORIGINS`).
- Документация — автоматический Swagger UI (`/docs`) и ReDoc (`/redoc`), плюс
  Postman-коллекция (`postman_collection.json`) и curl-примеры (`curl_examples.md`).

---

## 5. AI-интеграция

**Функция:** при получении обращения комментарий пользователя прогоняется через
Claude (Anthropic API) для:
1. **Анализа тональности** (`positive` / `neutral` / `negative`)
2. **Классификации типа обращения** (`project_inquiry`, `job_offer`, `collaboration`,
   `complaint`, `question`, `spam`, `other`)
3. **Генерации черновика ответа** — короткий, дружелюбный авто-ответ, который менеджер
   может отредактировать перед отправкой пользователю

Результат AI-анализа:
- попадает в письмо владельцу сайта (контекст для быстрой обработки заявки)
- используется как часть текста письма-копии пользователю
- возвращается в API-ответе
- учитывается в метриках (`/api/metrics`)

### Промпт

Системный промпт (`app/services/ai_service.py`, переменная `_SYSTEM_PROMPT`)
явно требует от модели вернуть **только валидный JSON** без markdown-обёртки,
с фиксированной схемой полей (`sentiment`, `category`, `auto_reply`), что
позволяет надёжно парсить ответ без хрупкого regex-парсинга свободного текста.

### Graceful fallback

Если:
- `ANTHROPIC_API_KEY` не задан или `AI_ENABLED=false`,
- запрос к Anthropic API превысил таймаут (`AI_TIMEOUT_SECONDS`, по умолчанию 8с),
- провайдер вернул ошибку (rate limit, недоступность, network error),
- ответ AI не удалось распарсить как JSON,

— сервис **не падает**, а прозрачно переключается на простую rule-based эвристику
(`_fallback_analysis` в `app/services/ai_service.py`): определение тональности по
ключевым словам, классификация по характерным фразам, заранее заготовленный
шаблон авто-ответа. Поле `provider` в ответе показывает, какой механизм
сработал (`anthropic` или `fallback`) — это видно и в API-ответе, и в письмах,
и в метриках.

Вызов Anthropic API выполняется в отдельном потоке (`asyncio.to_thread`) с
таймаутом через `asyncio.wait_for`, чтобы не блокировать event loop FastAPI
и не подвешивать запрос на неопределённое время.

---

## 6. Что сделано с помощью AI

Разработка велась с активным использованием Claude (Anthropic) в роли AI-ассистента
по написанию кода:

- **Сгенерировано с помощью AI:** каркас слоистой архитектуры (Controllers/Services/
  Repositories), Pydantic-схемы валидации, реализация file-based rate limiter со
  скользящим окном, потокобезопасный `JSONFileRepository` с атомарной записью через
  временный файл, интеграция с Anthropic API (system prompt + парсинг JSON-ответа +
  fallback-логика), email-сервис на `smtplib`, middleware логирования с request_id,
  глобальный error handler, демо-фронтенд (HTML/CSS/JS).
- **Промпты, которые использовались** (в обобщённом виде, в духе исходного ТЗ):
  - "Спроектируй слоистую архитектуру FastAPI-сервиса: Controllers → Services →
    Repositories, для формы обратной связи с email, AI-анализом, rate limiting
    и файловым хранением вместо БД"
  - "Напиши AI-сервис, который вызывает Anthropic API для анализа тональности и
    категории комментария, возвращает структурированный JSON, иgracefully
    переключается на rule-based fallback при любой ошибке/таймауте"
  - "Сделай потокобезопасный JSON-репозиторий поверх файловой системы с атомарной
    записью (через временный файл + os.replace) и file-level lock"
  - "Реализуй sliding-window rate limiter на файловом хранилище без внешних
    зависимостей типа Redis"
- **Что пришлось проверять/исправлять вручную:** запуск сервиса локально и
  end-to-end тестирование всех эндпоинтов (`/api/health`, `/api/contact`,
  `/api/metrics`) через curl, в том числе проверка edge-кейсов: невалидный email,
  отсутствующие поля, превышение rate limit (7 запросов подряд при лимите 5/час) —
  все сценарии проверены и работают корректно (см. логи в `logs/`); найдена и
  исправлена ошибка ложного срабатывания категоризации в rule-based fallback
  (фраза "не работает" ошибочно матчилась на ключевое слово "работа" → было
  переписано на проверку конкретных фраз с правильным приоритетом проверок).

---

## 7. Хранение данных

Файловая система используется вместо БД (согласно заданию). Все файлы лежат в
`data/` и создаются автоматически при первом запуске.

| Файл | Назначение | Формат |
|---|---|---|
| `data/contacts.json` | История обращений (последние 500), включая AI-анализ | JSON-массив |
| `data/metrics.json` | Агрегированная статистика (счётчики, breakdown по sentiment/category) | JSON-объект |
| `data/rate_limit.json` | Таймстемпы запросов по IP для sliding-window rate limiting | JSON-объект `{ip: [timestamps]}` |
| `logs/app.log` | Общий лог приложения: ошибки, AI, email, бизнес-события | текстовый, с ротацией (5MB × 5 файлов) |
| `logs/requests.log` | Лог всех HTTP-запросов (IP, метод, путь, статус, длительность, request_id) | текстовый, с ротацией |

### Rate limiting — как устроено

`app/services/rate_limiter.py` + `app/repositories/rate_limit_repository.py`:
sliding window по IP-адресу (учитывается `X-Forwarded-For`, если сервис стоит за
прокси). При каждом запросе читаются таймстемпы последних запросов с этого IP за
окно `RATE_LIMIT_WINDOW_SECONDS` (по умолчанию 3600с = 1 час); если их больше
`RATE_LIMIT_MAX_REQUESTS` (по умолчанию 5) — запрос отклоняется с `429`.

### Потокобезопасность файлового хранилища

`JSONFileRepository` (`app/repositories/json_file_repository.py`) — общий механизм
для всех файловых репозиториев:
- `threading.Lock` на каждый файл (по пути), чтобы избежать гонок при параллельных
  запросах внутри одного процесса
- атомарная запись: данные сначала пишутся во временный файл `*.tmp`, затем
  переименовываются (`os.replace`) — это исключает повреждение файла при сбое
  посередине записи
- устойчивость к повреждённому/пустому файлу — при ошибке парсинга JSON
  репозиторий откатывается на дефолтное значение вместо падения

---

## 8. Деплой

### Вариант A — Docker (рекомендуется)

```bash
docker build -t dev-landing-backend .
docker run -d -p 8000:8000 --env-file .env --name dev-landing dev-landing-backend
```

### Вариант B — локальный запуск + ngrok

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
# в другом терминале
ngrok http 8000
```

### Вариант C — Render / Railway

1. Запушить репозиторий на GitHub
2. Создать новый Web Service, указать:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Добавить переменные окружения из `.env.example` в настройках сервиса

### Если деплой недоступен — запуск локально

См. раздел [1. Как запустить проект](#1-как-запустить-проект) — сервис полностью
рабочий в локальном режиме без какого-либо внешнего деплоя, включая Swagger-документацию
и демо-фронтенд.

---

## Тестирование

Все эндпоинты проверены вручную (curl) в процессе разработки:
- ✅ `POST /api/contact` — успешный сценарий (200, корректный AI-анализ, попытка отправки писем)
- ✅ `POST /api/contact` — невалидный email (422)
- ✅ `POST /api/contact` — отсутствующие обязательные поля (422)
- ✅ `POST /api/contact` — rate limiting (429 после превышения лимита)
- ✅ `GET /api/health` — корректный статус и флаги конфигурации
- ✅ `GET /api/metrics` — корректная агрегация статистики
- ✅ `GET /docs`, `/redoc`, `/openapi.json` — документация доступна
- ✅ `GET /static/index.html` — демо-фронтенд отдаётся и работает с API

Готовые сценарии для проверки — `postman_collection.json` (импортируется в Postman)
и `curl_examples.md`.
# testproject

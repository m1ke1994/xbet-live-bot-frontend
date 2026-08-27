# Backend видимого Chromium

FastAPI управляет одной persistent-сессией Playwright Chromium. Backend открывает сайт, визуально заполняет форму входа и сохраняет cookies/localStorage в `playwright-profile/`. Автоматические ставки, догон, поиск матчей и обход защит здесь не реализованы.

## Установка на Windows

Требуется Python 3.11 или новее. Все команды выполняются из папки `backend`:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium

Copy-Item .env.example .env
```

Откройте `.env` и вручную задайте `XBET_LOGIN` и `XBET_PASSWORD`. Каноническое расположение — `backend/.env`; для совместимости также поддерживается существующий `backend/app/.env`. Оба пути вычисляются абсолютно и не зависят от текущей директории Uvicorn. Эти данные берет только backend; API не принимает и не возвращает пароль. Файл `.env` и профиль Chromium исключены из Git.

## Запуск

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Swagger UI: <http://127.0.0.1:8000/docs>

Порядок ручной проверки:

1. `GET /health` должен вернуть `{"status":"ok"}`.
2. `POST /api/browser/start` запускает Chromium и открывает сайт.
3. `GET /api/browser/state` показывает URL, title и статус сессии.
4. `GET /api/browser/config-check` безопасно подтверждает загрузку настроек без возврата секретов.
5. `POST /api/browser/open-login` находит «Вход», нажимает его и ждёт появления точных полей `input#username` и `input#username-password[type="password"]`.
6. `POST /api/browser/fill-login` заполняет оба поля данными из `.env` и проверяет, что значения появились.
7. `POST /api/browser/login` или `POST /api/browser/full-login` выполняет полный сценарий: открыть → заполнить → безопасно найти submit внутри формы → отправить.
8. `POST /api/browser/stop` закрывает Chromium и Playwright.

Кнопка отправки никогда не ищется глобально. Если внутри формы не найден надёжный submit, Chromium остаётся открытым, а API возвращает `CREDENTIALS_FILLED` с пояснением.

Повторный `POST /api/browser/start` использует уже открытое окно и не создает второй Chromium. Между перезапусками cookies и localStorage сохраняются в `playwright-profile/`.

## Статусы

- `STOPPED`, `STARTING`, `OPENED` — жизненный цикл окна;
- `OPENING_LOGIN`, `LOGIN_FORM_OPENED` — открытие и обнаружение формы;
- `FILLING_CREDENTIALS`, `CREDENTIALS_FILLED` — заполнение точных полей;
- `SUBMITTING_LOGIN`, `LOGIN_SUBMITTED` — безопасная отправка формы;
- `AUTHENTICATED` — состояние входа надежно обнаружено по DOM;
- `AUTH_STATE_UNKNOWN` — нет ни кнопки входа, ни надёжного признака профиля;
- `MANUAL_ACTION_REQUIRED` — видна CAPTCHA, SMS-код или дополнительная проверка;
- `ERROR` — автоматический сценарий остановился с ошибкой.

При `MANUAL_ACTION_REQUIRED` Chromium остается открытым: проверку нужно завершить вручную. Backend не обходит CAPTCHA или антибот-защиту. Если селекторы сайта изменились, API возвращает понятную ошибку и также оставляет окно открытым.

При ошибке авторизации `detail` содержит этап, URL и факты обнаружения полей/submit. Диагностический screenshot сохраняется в `backend/diagnostics/`; credential-поля на нём маскируются средствами Playwright, а директория исключена из Git.

## Где появляется окно

Playwright запускается строго с `headless=False` и `slow_mo`, поэтому Chromium показывается на той машине, где физически запущен backend. Текущий сценарий рассчитан на локальный запуск backend на Windows. Docker на этом этапе не используется, поскольку он усложнил бы вывод GUI-окна.

Следующий этап после стабильной авторизации — навигация Live → Киберспорт → поиск активной команды. В текущую реализацию он намеренно не входит.

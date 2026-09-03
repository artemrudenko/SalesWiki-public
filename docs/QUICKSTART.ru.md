# SalesWiki: быстрый старт (5 минут)

Самый короткий путь увидеть SalesWiki в работе — на безопасных синтетических
demo-данных, без реальной информации о клиентах. Полная настройка описана в
[SETUP.en.md](SETUP.en.md) (документация проекта ведётся на английском; эта
страница — единственное русскоязычное исключение, кратчайший путь к первой пользе).

## 1. Что нужно

- Obsidian (бесплатный) — чтобы открыть vault и дашборды.
- Python 3 — на macOS уже есть; нужен для refresh-скриптов и MCP gateway.
- Claude Code, Claude Desktop или Cowork — основной способ задавать вопросы
  обычным языком (опционально, если нужен только просмотр в Obsidian).

## 2. Посмотреть (1 минута)

Из корня репозитория запустите first-run assistant:

```bash
python3 scripts/first_run.py
```

Он создаёт `.venv`, ставит зависимости, проверяет public snapshot и запускает
permissioned demo smoke test.

1. Откройте Obsidian → `Open folder as vault` → выберите папку `SalesWiki`.
2. Откройте `demo/reports/dashboard-snapshots/sales-today.md` — наполненный
   дашборд «что делать сегодня»: горячие лиды, рисковые сделки, score и даты ревью.
3. Кликните любую строку, чтобы открыть карточку, например
   `demo/demo-vault/wiki/entities/deals/Deal - Atlas Robotics - Pilot.md`.

Всё внутри `demo/` — синтетика (`synthetic: true`): изучайте свободно,
утечь нечему.

Хотите перезапустить только smoke-тест permissioned-слоя? Он прогоняет контраст
ролей, no-leak и полную governance-петлю на одноразовом vault и печатает
PASS/FAIL:

```bash
python3 scripts/demo_dryrun.py
```

## 3. Задать вопросы (3 минуты)

Основной способ спросить — Claude MCP-клиент (**Claude Code, Claude Desktop
или Cowork**), подключённый к permissioned MCP gateway. (Опциональное чат-демо
в Rocket.Chat для аудитории без Claude-клиента — в конце раздела.)

### Claude Code / Claude Desktop / Cowork (MCP gateway)

Permissioned MCP gateway отвечает на вопросы по demo vault с цитатами и
ролевым доступом. Если вы уже запустили `scripts/first_run.py`, виртуальное
окружение готово. Сгенерируйте config:

```bash
.venv/bin/python scripts/generate_mcp_demo_config.py --personas ae,marketing,curator
```

Вставьте сгенерированный блок `mcpServers` в Claude Code, Claude Desktop,
Cowork или другой MCP-клиент, перезапустите клиент и спросите:

1. *«Что мне делать сегодня?»* → `my_day` — лиды и риски сделок одним дайджестом.
2. *«Дай бриф по BluePeak Energy»* → `company_brief` — выжимка с цитатами;
   содержание зависит от вашей роли.
3. *«Какие сделки под риском?»* → `deal_risk` — факторы риска и следующие шаги.

Demo-роли (задаются через `SALESWIKI_DEMO_ACTOR`): `demo-ethan-ae` (аккаунт-менеджер),
`demo-olivia-marketing` (маркетинг), `demo-claire-hos` (руководитель продаж),
`demo-sophie-curator` (куратор/аппрувер), `demo-broad-viewer` (наблюдатель).
Подключите две записи с разными ролями параллельно, чтобы увидеть ролевой
контраст: маркетинг не видит экономику сделок, а персональные данные остаются
handle вида `restricted://`. Полный сценарий демо:
[engineering/permissioned-knowledge-demo-runbook.md](engineering/permissioned-knowledge-demo-runbook.md).

> Demo-идентичность — это серверная env-настройка: подходит для демо и пилота
> с одним оператором, но это ещё не настоящая многопользовательская
> аутентификация (SSO — следующая фаза; см.
> `docs/engineering/permissioned-knowledge-sso-design.md`).

### Опционально: чат-демо в Rocket.Chat (без Claude-клиента и без `.venv`)

Опциональное чат-демо того же permissioned vault — удобно показать ролевой
доступ аудитории без Claude-клиента: спрашиваете в канале, переключаете роль
командой и видите те же правила доступа. Режим по умолчанию импортирует
in-repo core напрямую — только стандартная библиотека, без virtualenv.

```bash
export RC_URL="https://your-rocketchat"   # доступный вам сервер
export RC_USER="your-login"               # обычный пользователь
export RC_PASS="your-password"
export RC_CHANNEL="saleswiki-demo"        # существующий канал, без '#'
python3 integrations/rocketchat/bridge.py
```

Затем наберите `демо` в канале — выведется полная шпаргалка. Полный список
команд, предусловия и режим real-MCP: `integrations/rocketchat/README.md`.

## 4. Поддерживать свежесть (1 команда)

После любого изменения карточек одна команда валидирует vault и перестраивает
индексы и снапшоты дашбордов:

```bash
python3 scripts/refresh.py          # production-данные
python3 scripts/refresh.py --demo   # demo-данные
```

## 5. Куда дальше

- Добавить первый реальный запрос: запишите свободным текстом в
  `state/manual-intake.md` — агент превратит его в полноценную карточку
  (см. `wiki/processes/manual-intake.md`).
- Работаете с реальными данными продаж? Сначала прочитайте контракт пилотных
  данных: `wiki/processes/pilot-data-contract.md` — он не даёт реальным данным
  попасть в этот репозиторий и смешаться с demo.
- Ежедневная работа: [USER_GUIDE.en.md](USER_GUIDE.en.md).
- Demo guide: [DEMO.en.md](DEMO.en.md).
- Как устроен permissioned-слой: `docs/engineering/permissioned-knowledge-overview.md`.

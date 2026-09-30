# Lichess Puzzle Viewer

Графическое desktop-приложение на Python/Tkinter для просмотра, фильтрации и экспорта задач из открытой базы Lichess.

## Возможности

- Импорт `lichess_db_puzzle.csv` в локальную SQLite базу
- Пакетная вставка с индексами, WAL-режим, кэш фильтров/статистики
- Фильтрация по:
  - цвету хода, точному числу полуходов
  - стандартным темам с категориями
  - пользовательским темам: включение и исключение
  - рейтингу, популярности, количеству разборов
  - дебютам, дате
- Пагинация результатов и debounce фильтров
- Пошаговое проигрывание решения с подсветкой хода
- Рендер доски: PIL юникод-фигуры или SVG с кэшем из Lichess CDN
- Выбор задач и экспорт в DOCX:
  - 12 задач на страницу, сетка 4×3
  - Автосоздание файла ответов
  - Сохранение пользовательских тем в БД
- Двуязычный интерфейс: русский/английский

## Стек

- Python 3.9+
- Tkinter
- SQLite
- Pillow, python-chess, cairosvg, requests, python-docx

## Быстрый старт

```bash
python main.py
```

При первом запуске импортируйте `lichess_db_puzzle.csv` через меню.

## Зависимости

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
python main.py
```

## Логи экспорта DOCX

Файл `docx_export.log` создаётся автоматически в папке проекта.

Архивирование логов происходит автоматически при старте приложения в фоновом потоке:
- `docx_export.log` переименовывается в `docx_export-YYYYMMDD-HHMMSS.log` и сжимается в `.gz`
- архивы старше 10 дней удаляются

Это не замедляет запуск приложения, так как archivирование выполняется в отдельном потоке.

### Ручной запуск

```bash
python log_archive.py
```

## Тесты

```bash
python -m unittest tests -v
```

### Linux

Без графической сессии используйте `xvfb-run`:

```bash
xvfb-run -a python -m unittest tests -v
```

Если в системном Python отсутствует `PIL.ImageTk`, запускайте тесты из `venv`:

```bash
python3 -m venv .venv
.venv/bin/pip install Pillow python-chess cairosvg requests python-docx
xvfb-run -a .venv/bin/python -m unittest tests -v
```

### Windows

```bash
python -m venv .venv
.venv\Scripts\pip install Pillow python-chess cairosvg requests python-docx
.venv\Scripts\python -m unittest tests -v
```

### Примечание

Тесты DOCX-экспорта не пишут файлы в папку проекта: они используют `tempfile.mkstemp()` и удаляют временные файлы после проверки. Для перегенерации тестовых DOCX используйте скрипт:

```bash
PYTHONPATH=. xvfb-run -a python regenerate_test_docx.py
```

---

## Иконка приложения

Приложение поддерживает иконку окна:

- Windows: `icon.ico`
- Linux: `icon.png`

Если файл иконки находится в папке с приложением, он подтягивается автоматически при старте.

Рекомендуемые размеры:
- `icon.ico`: 256×256, 128×128, 64×64, 48×48, 32×32, 16×16
- `icon.png`: 512×512

### Где взять иконку

Можно использовать любую шахматную иконку в формате `.ico` или `.png`. Например:
- https://icons8.com/icons/set/chess
- https://www.flaticon.com/search?word=chess

### Сборка с иконкой

#### Linux

```bash
pyinstaller --onefile --windowed \
  --name "Lichess Puzzle Viewer" \
  --add-data "lichess_themes.json:." \
  --add-data "icon.png:." \
  main.py
```

#### Windows

```powershell
.venv\Scripts\pyinstaller --onefile --windowed --name "Lichess Puzzle Viewer" --add-data "lichess_themes.json;." --add-data "icon.ico;." main.py
```

При запуске собранного `exe` иконка будет отображаться в заголовке окна и на панели задач.

## Сборка и установка

### Linux

#### Требования

- Python 3.9+
- `python3-venv`, `python3-pip`, `python3-tk`
- Системные библиотеки для Pillow и cairosvg:
  - Debian/Ubuntu: `libjpeg-dev`, `zlib1g-dev`, `libcairo2`

#### Запуск из исходников

```bash
git clone <repo-url>
cd lichess_tasks
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install Pillow python-chess cairosvg requests python-docx pyinstaller
python main.py
```

#### Сборка в исполняемый файл

```bash
pyinstaller --onefile --windowed \
  --name "Lichess Puzzle Viewer" \
  --add-data "lichess_themes.json:." \
  --add-data "icon.png:." \
  main.py
```

Готовый файл будет в `dist/Lichess Puzzle Viewer`.

### Windows

#### Требования

- Python 3.9+
- Visual C++ Redistributable (для некоторых пакетов)

#### Запуск из исходников

```powershell
git clone <repo-url>
cd lichess_tasks
python -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install Pillow python-chess cairosvg requests python-docx pyinstaller
.venv\Scripts\python main.py
```

#### Сборка в `exe`

```powershell
.venv\Scripts\pyinstaller --onefile --windowed --name "Lichess Puzzle Viewer" --add-data "lichess_themes.json;." --add-data "icon.ico;." main.py
```

Готовый `exe` будет в `dist\Lichess Puzzle Viewer.exe`.

При запуске `exe` создаётся папка рядом с ним, где хранятся:
- `puzzles.db` — база задач
- `docx_export.log` — лог экспорта
- `docx_export-*.log.gz` — архивы логов

### macOS

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install Pillow python-chess cairosvg requests python-docx pyinstaller
python3 main.py
```

Сборка `app` через `pyinstaller` аналогична Linux.

## Структура проекта

- `main.py` — точка входа
- `ui.py` — главное окно приложения
- `ui_filters.py` — фильтры и статистика
- `ui_themes.py` — темы и категории
- `ui_selection.py` — панель выбранных задач и экспорт
- `ui_puzzle_view.py` — просмотр задачи и решение
- `ui_import.py` — импорт CSV
- `database.py` — SQLite база, фильтрация, кэш
- `board_renderer.py` — ренер доски
- `docx_exporter.py` — экспорт в DOCX
- `constants.py` — константы, переводы
- `log_archive.py` — архивирование логов
- `tests.py` — тесты

## Лицензия

MIT

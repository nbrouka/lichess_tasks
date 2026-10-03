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

## Репозиторий

https://github.com/nbrouka/lichess_tasks.git

## Стек

- Python 3.9+
- Tkinter
- SQLite
- Pillow, python-chess, cairosvg, requests, python-docx, zstandard

## Быстрый старт

### Автоматическая установка

Скрипт сам установит:
- Системные зависимости (`python3-tk`, `libjpeg`, `cairo`, `zstd`, `curl`)
- Виртуальное окружение Python
- Python-зависимости из `requirements.txt`
- Скачает `lichess_db_puzzle.csv` (~2GB) с https://database.lichess.org/

**Linux / macOS:**
```bash
chmod +x install.sh
./install.sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

**Windows (cmd):**
```cmd
install.bat
```

### Ручная установка

```bash
git clone https://github.com/nbrouka/lichess_tasks.git
cd lichess_tasks
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
python main.py
```

При первом запуске импортируйте `lichess_db_puzzle.csv` через меню, если скрипт не скачал его автоматически.

## Системные требования

### Общие
- Python 3.9+
- Виртуальное окружение (рекомендуется)
- `lichess_themes.json` — файл с темами Lichess (должен лежать в корне проекта)
- `lichess_db_puzzle.csv` — база задач Lichess для импорта

### Зависимости Python

```
pillow
python-docx
cairosvg
chess
requests
zstandard
```

> Примечание: скрипты установки (`install.sh`, `install.ps1`, `install.bat`) автоматически установят все зависимости, включая системные.

### Linux

Установите системные пакеты:

```bash
# Debian/Ubuntu
sudo apt install python3-venv python3-pip python3-tk \
                 libjpeg-dev zlib1g-dev libcairo2

# Fedora
sudo dnf install python3-tkinter libjpeg-turbo-devel zlib-devel cairo-devel

# Arch
sudo pacman -S tk libjpeg-turbo cairo
```

### Windows

- Python 3.9+ с опцией `tcl/tk and IDLE`
- Visual C++ Redistributable (для некоторых пакетов)

### macOS

```bash
brew install python-tk cairo
```

## База задач

Скрипты установки автоматически скачивают `lichess_db_puzzle.csv` (~2GB) с https://database.lichess.org/ и распаковывают его в корень проекта.

Если вы хотите скачать CSV отдельно:

```bash
# Linux/macOS
curl -L -o lichess_db_puzzle.csv.zst https://database.lichess.org/lichess_db_puzzle.csv.zst
zstd -d lichess_db_puzzle.csv.zst

# Windows (PowerShell)
curl.exe -L -o lichess_db_puzzle.csv.zst https://database.lichess.org/lichess_db_puzzle.csv.zst
.venv\Scripts\python.exe -c "import zstandard; ..."
```

## Импорт CSV из терминала

Для импорта без запуска GUI используйте `import_csv.py`:

```bash
python import_csv.py [csv_path] [db_path]
```

Пример:

```bash
python import_csv.py lichess_db_puzzle.csv puzzles.db
```

По умолчанию используются:
- CSV: `lichess_db_puzzle.csv`
- БД: `puzzles.db`

Скрипт сравнивает количество задач в CSV и в локальной БД и выводит результат проверки.

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
.venv/bin/pip install Pillow python-chess cairosvg requests python-docx zstandard
xvfb-run -a .venv/bin/python -m unittest tests -v
```

### Windows

```bash
python -m venv .venv
.venv\Scripts\pip install Pillow python-chess cairosvg requests python-docx zstandard
.venv\Scripts\python -m unittest tests -v
```

### Примечание

Тесты DOCX-экспорта не пишут файлы в папку проекта: они используют `tempfile.mkstemp()` и удаляют временные файлы после проверки. Для перегенерации тестовых DOCX используйте скрипт:

```bash
PYTHONPATH=. xvfb-run -a python regenerate_test_docx.py
```

---

## Иконка приложения

Приложение поддерживает иконки:
- `icon.ico` — для Windows
- `icon.png` — для Linux
- `icon.svg` — векторная версия

Если нужно добавить иконку, положите файлы с такими именами в корень проекта.

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

## Репозиторий

https://github.com/nbrouka/lichess_tasks.git

## Сборка и установка

### Автоматическая установка

Скрипты (`install.sh`, `install.ps1`, `install.bat`) автоматически:
- Установят системные зависимости (`python3-tk`, `libjpeg`, `cairo`, `zstd`, `curl`)
- Создадут виртуальное окружение Python
- Установят Python-зависимости из `requirements.txt`
- Скачают `lichess_db_puzzle.csv` (~2GB) с https://database.lichess.org/ и распакуют

### Linux

#### Требования

- Python 3.9+
- `python3-venv`, `python3-pip`, `python3-tk`
- Системные библиотеки для Pillow и cairosvg:
  - Debian/Ubuntu: `libjpeg-dev`, `zlib1g-dev`, `libcairo2`
  - Fedora: `libjpeg-turbo-devel`, `zlib-devel`, `cairo-devel`
  - Arch: `libjpeg-turbo`, `cairo`

#### Запуск из исходников

```bash
git clone https://github.com/nbrouka/lichess_tasks.git
cd lichess_tasks
chmod +x install.sh
./install.sh
```

Или вручную:
```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
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

- Python 3.9+ с опцией `tcl/tk and IDLE`
- Visual C++ Redistributable (для некоторых пакетов)

#### Запуск из исходников

```powershell
git clone https://github.com/nbrouka/lichess_tasks.git
cd lichess_tasks
powershell -ExecutionPolicy Bypass -File install.ps1
```

Или вручную:
```powershell
python -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt
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
git clone https://github.com/nbrouka/lichess_tasks.git
cd lichess_tasks
chmod +x install.sh
./install.sh
```

Или вручную:
```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
python3 main.py
```

Сборка `app` через `pyinstaller` аналогична Linux.

## Структура проекта

- `main.py` — точка входа
- `import_csv.py` — CLI для импорта CSV в локальную БД
- `ui.py` — главное окно приложения
- `ui_filters.py` — фильтры и статистика
- `ui_themes.py` — темы и категории
- `ui_selection.py` — панель выбранных задач и экспорт
- `ui_puzzle_view.py` — просмотр задачи и решение
- `ui_import.py` — импорт CSV через GUI
- `database.py` — SQLite база, фильтрация, кэш
- `board_renderer.py` — ренер доски
- `docx_exporter.py` — экспорт в DOCX
- `constants.py` — константы, переводы
- `log_archive.py` — архивирование логов
- `tests.py` — тесты

## Лицензия

MIT

# Lichess Puzzle Viewer

Графическое приложение на Python/Tkinter для просмотра и фильтрации задач из открытой базы Lichess, с экспортом в DOCX.

## Возможности

- Импорт `lichess_db_puzzle.csv` в SQLite
- Фильтрация по цвету, количеству ходов, темам, рейтингу, популярности, дебютам
- Пошаговое проигрывание решения
- Выбор задач и экспорт в DOCX с автосозданием файла ответов
- Двуязычный интерфейс: русский/английский

## Запуск

```bash
python main.py
```

## Зависимости

- Pillow
- python-chess
- cairosvg
- requests
- python-docx

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

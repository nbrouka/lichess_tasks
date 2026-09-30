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

### Linux

Для автоматического архивирования логов добавьте в crontab:

```bash
crontontab -l 2>/dev/null; echo "0 3 * * * /usr/bin/python3 /home/anduser/python/lichess_tasks/log_archive.py >> /home/anduser/python/lichess_tasks/log_archive.log 2>&1" | crontab -
```

Это запустит `log_archive.py` каждый день в 03:00. Скрипт:
- переименовывает `docx_export.log` в `docx_export-YYYYMMDD-HHMMSS.log`
- сжимает его в `.gz`
- удаляет архивы старше 10 дней

### Windows

Для автоматического архивирования логов используйте `Планировщик заданий`:

1. Откройте `Планировщик заданий` (`taskschd.msc`)
2. Создайте простую задачу
3. Триггер: ежедневно, время запуска — `03:00`
4. Действие: запуск программы
5. Программа: путь к Python, например:
   ```
   C:\Python39\python.exe
   ```
6. Аргументы:
   ```
   C:\path\to\lichess_tasks\log_archive.py
   ```
7. В разделе `Настройка` отметьте `Выполнить, даже если пользователь не вошёл в систему`
8. В `Условия` отметьте `Запускать только при питании от электросети`

Скрипт `log_archive.py`:
- переименовывает `docx_export.log` в `docx_export-YYYYMMDD-HHMMSS.log`
- сжимает его в `.gz`
- удаляет архивы старше 10 дней

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

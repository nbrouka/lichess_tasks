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

## Рефакторинг

В проекте применены следующие улучшения:

- **Константы**: все magic numbers и хардкодные строки вынесены в `constants.py` (размеры окон, панелей, параметры DOCX, отступы, границы ячеек)
- **Централизация логики**: добавлен хелпер `current_player_color_name()` для определения текущего цвета, убрано дублирование `"Ход белых" / "Ход черных"`
- **Удаление дубликатов**: устранён дубликат темы `dovetailMate` в `constants.py`
- **Кэширование фигур**: исправлено кэширование `PieceSet` — теперь используется классовый кэш по ключу `{symbol}_{size}`, ранее каждый `render_puzzle` создавал новый экземпляр с пустым кэшем
- **Разбиение функций**: длинный метод `_create_answers_docx` разбит на `_format_answers_solution()`
- **Type hints**: добавлены аннотации типов для ключевых методов и классов
- **Неиспользуемые импорты**: удалены неиспользуемые модули (`hashlib`, `os`, `tempfile` и др.)

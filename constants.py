"""
Константы и общие настройки приложения Lichess Puzzle Viewer.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Приложение
# ---------------------------------------------------------------------------
APP_NAME = "Lichess Puzzle Viewer"
VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Пути к данным
# ---------------------------------------------------------------------------
DEFAULT_CSV_PATH = "lichess_db_puzzle.csv"
DB_FILENAME = "puzzles.db"
ICON_WINDOWS = "icon.ico"
ICON_LINUX = "icon.png"

# ---------------------------------------------------------------------------
# Шахматная доска
# ---------------------------------------------------------------------------
SQUARE_SIZE = 60
BOARD_SIZE = SQUARE_SIZE * 8
COLOR_LIGHT = "#F0D9B5"
COLOR_DARK = "#B58863"
COLOR_COORDINATES = "#000000"

# ---------------------------------------------------------------------------
# Юникод-фигуры (ключ — символ python-chess)
# ---------------------------------------------------------------------------
PIECE_UNICODE = {
    "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
    "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚",
}

# ---------------------------------------------------------------------------
# Темы задач
# ---------------------------------------------------------------------------
THEME_TRANSLATIONS = {
    "advancedPawn": "Продвинутая пешка",
    "attackingF2F7": "Атака на f2/f7",
    "capturingDefender": "Захват защитника",
    "discoveredAttack": "Открытая атака",
    "doubleCheck": "Двойной шах",
    "exposedKing": "Открытый король",
    "fork": "Вилка",
    "hangingPiece": "Висячая фигура",
    "kingsideAttack": "Атака на королевском фланге",
    "pin": "Привязка",
    "queensideAttack": "Атака на ферзевом фланге",
    "sacrifice": "Жертва",
    "skewer": "Шпиль",
    "trappedPiece": "Запертая фигура",
    "attraction": "Привлечение",
    "clearance": "Расчистка",
    "defensiveMove": "Защитительный ход",
    "deflection": "Отвлечение",
    "interference": "Вмешательство",
    "intermezzo": "Интермеццо",
    "quietMove": "Тихий ход",
    "xRayAttack": "Рентгеновская атака",
    "zugzwang": "Цугцванг",
    "mate": "Мат",
    "mateIn1": "Мат в 1",
    "mateIn2": "Мат в 2",
    "mateIn3": "Мат в 3",
    "mateIn4": "Мат в 4",
    "mateIn5": "Мат в 5+",
    "anastasiaMate": "Мат Анастасии",
    "arabianMate": "Аравийский мат",
    "backRankMate": "Мат на последней горизонтали",
    "bodenMate": "Мат Бодена",
    "doubleBishopMate": "Двойной слоновий мат",
    "dovetailMate": "Мат «голубка»",
    "hookMate": "Мат «крючок»",
    "smotheredMate": "Задушенный мат",
    "castling": "Рокировка",
    "enPassant": "Взятие на проходе",
    "promotion": "Превращение пешки",
    "underPromotion": "Превращение в неферзя",
    "equality": "Равенство",
    "advantage": "Преимущество",
    "crushing": "Разгромное преимущество",
    "oneMove": "Однодходовка",
    "short": "Короткая",
    "long": "Длинная",
    "veryLong": "Очень длинная",
    "master": "Мастерские игры",
    "masterVsMaster": "Мастер против мастера",
    "superGM": "Супер GM",
    "opening": "Дебют",
    "middlegame": "Миттельшпиль",
    "endgame": "Эндшпиль",
    "rookEndgame": "Эндшпиль с ладьями",
    "bishopEndgame": "Слоновый эндшпиль",
    "pawnEndgame": "Пешечный эндшпиль",
    "knightEndgame": "Коневый эндшпиль",
    "queenEndgame": "Ферзевый эндшпиль",
    "queenRookEndgame": "Ферзь + ладья",
    "collinearMove": "Коллинеарный ход",
    "cornerMate": "Угловой мат",
    "epauletteMate": "Мат «эполет»",
    "killBoxMate": "Мат в «kill box»",
    "morphysMate": "Мат Морфи",
    "operaMate": "Оперный мат",
    "pillsburysMate": "Мат Пиллсбери",
    "swallowstailMate": "Мат «хвост ласточки»",
    "triangleMate": "Треугольный мат",
    "vukovicMate": "Мат Вуковича",
    "blindSwineMate": "Мат «слепой свиньи»",
    "discoveredCheck": "Открытый шах",
    "playerGames": "Игры игроков",
    "healthyMix": "Сбалансированная подборка",
}

THEME_RU_TO_EN = {v: k for k, v in THEME_TRANSLATIONS.items()}

CATEGORY_TRANSLATIONS = {
    "Recommended": "Рекомендуемые",
    "Phases": "Фазы",
    "By openings": "По дебютам",
    "Motifs": "Мотивы",
    "Advanced": "Продвинутые",
    "Mates": "Мат",
    "Mate themes": "Темы мата",
    "Special moves": "Специальные ходы",
    "Goals": "Цели",
    "Lengths": "Длина",
    "Origin": "Источник",
}

CATEGORY_RU_TO_EN = {v: k for k, v in CATEGORY_TRANSLATIONS.items()}

UI_TRANSLATIONS = {
    "ru": {
        "app_title": "Lichess Puzzle Viewer",
        "menu_file": "Файл",
        "menu_help": "Справка",
        "menu_open_csv": "Открыть CSV...",
        "menu_import_csv": "Импорт CSV",
        "menu_exit": "Выход",
        "menu_about": "О программе",
        "filters_title": "Фильтры",
        "moves_label": "Ходов:",
        "moves_explanation": "(точное количество ходов)",
        "toggle_filter_on": "Включить фильтр",
        "toggle_filter_off": "Выключить фильтр",
        "color_label": "Цвет:",
        "color_white": "Ход белых",
        "color_black": "Ход черных",
        "category_label": "Категория:",
        "themes_label": "Темы (выбрать):",
        "apply_btn": "Применить",
        "reset_btn": "Сбросить",
        "found_label": "Найдено: {count}",
        "prev_btn": "◀ Предыдущая",
        "save_png_btn": "Сохранить PNG",
        "next_btn": "Следующая ▶",
        "status_ready": "Готово.",
        "status_filtering": "Фильтрация",
        "status_loaded": "Загружено {count} задач (из {total})",
        "status_not_found": "Ничего не найдено.",
        "status_reset": "Фильтры сброшены.",
        "status_import_started": "Импорт запущен",
        "status_import_complete": "Импорт завершён.",
        "status_db_ready": "База готова.",
        "status_db_not_ready": "База не импортирована. Нажмите «Импорт CSV».",
        "status_loading": "Загрузка",
        "progress_title": "Импорт CSV",
        "progress_preparing": "Подготовка",
        "progress_importing": "Импортируем: {filename}",
        "progress_pct": "Импорт: {pct}% ({current:,} / {total_lines:,})",
        "puzzle_info": "Задача {index} из {total}",
        "no_data": "Нет данных",
        "theme_count_label": "Задач: {count}",
        "scale_from": "от {value}",
        "scale_to": "до {value}",
        "scale_equals": "= {value}",
        "select_btn": "Выбрать",
        "selected_title": "Выбранные задачи:",
        "msg_saved": "Сохранено: {path}",
        "msg_import_running": "Импорт уже выполняется.",
        "msg_import_success": "Импорт завершён!",
        "msg_import_error": "Ошибка импорта",
        "msg_select_puzzle": "Сначала выберите задачу.",
        "msg_no_selected_puzzles": "Нет выбранных задач.",
        "about_title": "О программе",
        "about_text": "Lichess Puzzle Viewer\nПросмотр и фильтрация задач из открытой базы Lichess.\n\nБаза: https://database.lichess.org/#puzzles",
        "progress_title": "Импорт CSV",
        "progress_preparing": "Подготовка",
        "progress_importing": "Импортируем: {filename}",
        "progress_pct": "Импорт: {pct}% ({current:,} / {total_lines:,})",
        "stats_white": "Ход белых: {white}",
        "stats_black": "Ход черных: {black}",
        "stats_by_moves": "По ходам: {moves}",
        "user_themes_label": "Пользовательские темы:",
    },
    "en": {
        "app_title": "Lichess Puzzle Viewer",
        "menu_file": "File",
        "menu_help": "Help",
        "menu_open_csv": "Open CSV...",
        "menu_import_csv": "Import CSV",
        "menu_exit": "Exit",
        "menu_about": "About",
        "filters_title": "Filters",
        "moves_label": "Moves:",
        "moves_explanation": "(exact number of moves)",
        "toggle_filter_on": "Enable filter",
        "toggle_filter_off": "Disable filter",
        "color_label": "Color:",
        "color_white": "White to move",
        "color_black": "Black to move",
        "category_label": "Category:",
        "themes_label": "Themes (select):",
        "user_themes_label": "User themes:",
        "apply_btn": "Apply",
        "reset_btn": "Reset",
        "found_label": "Found: {count}",
        "select_btn": "Select",
        "selected_title": "Selected puzzles:",
        "prev_btn": "◀ Previous",
        "save_png_btn": "Save PNG",
        "next_btn": "Next ▶",
        "status_ready": "Ready.",
        "status_filtering": "Filtering",
        "status_loaded": "Loaded {count} puzzles (from {total})",
        "status_not_found": "No results found.",
        "status_reset": "Filters reset.",
        "status_import_started": "Import started",
        "status_import_complete": "Import complete.",
        "status_db_ready": "Database ready.",
        "status_db_not_ready": "Database not imported. Click «Import CSV».",
        "status_loading": "Loading",
        "progress_title": "Import CSV",
        "progress_preparing": "Preparing",
        "progress_importing": "Importing: {filename}",
        "progress_pct": "Import: {pct}% ({current:,} / {total_lines:,})",
        "puzzle_info": "Puzzle {index} of {total}",
        "no_data": "No data",
        "theme_count_label": "Puzzles: {count}",
        "scale_from": "from {value}",
        "scale_to": "to {value}",
        "scale_equals": "= {value}",
        "msg_saved": "Saved: {path}",
        "select_btn": "Select",
        "selected_title": "Selected puzzles:",
        "msg_import_running": "Import already in progress.",
        "msg_import_success": "Import complete!",
        "msg_import_error": "Import error",
        "msg_select_puzzle": "Please select a puzzle first.",
        "msg_no_selected_puzzles": "No selected puzzles.",
        "about_title": "About",
        "about_text": "Lichess Puzzle Viewer\nBrowse and filter puzzles from the public Lichess database.\n\nDatabase: https://database.lichess.org/#puzzles",
        "progress_title": "Import CSV",
        "progress_preparing": "Preparing",
        "progress_importing": "Importing: {filename}",
        "progress_pct": "Import: {pct}% ({current:,} / {total_lines:,})",
        "stats_white": "White to move: {white}",
        "stats_black": "Black to move: {black}",
        "stats_by_moves": "By moves: {moves}",
        "user_themes_label": "User themes:",
    },
}

LANG = "ru"

COLOR_RU_TO_EN = {
    "Ход белых": "w",
    "Ход черных": "b",
}

def t(key: str, **kwargs) -> str:
    text = UI_TRANSLATIONS.get(LANG, UI_TRANSLATIONS["en"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


def current_player_color_name(stored_color: str) -> str:
    """Returns Russian name of the color currently to move,
    based on the stored color of the side that just moved."""
    return "Ход белых" if stored_color == "b" else "Ход черных"

THEME_CATEGORIES = [
    ("Рекомендуемые", ["healthyMix"]),
    ("Фазы", ["opening", "middlegame", "endgame", "rookEndgame", "bishopEndgame", "pawnEndgame", "knightEndgame", "queenEndgame", "queenRookEndgame"]),
    ("По дебютам", ["sicilianDefense", "frenchDefense", "queensPawnGame", "italianGame", "carokannDefense", "scandinavianDefense", "queensGambitDeclined", "englishOpening", "ruyLopez", "scotchGame", "indianDefense", "philidorDefense"]),
    ("Мотивы", ["advancedPawn", "attackingF2F7", "capturingDefender", "discoveredAttack", "doubleCheck", "exposedKing", "fork", "hangingPiece", "kingsideAttack", "pin", "queensideAttack", "sacrifice", "skewer", "trappedPiece"]),
    ("Продвинутые", ["attraction", "clearance", "collinearMove", "discoveredCheck", "defensiveMove", "deflection", "interference", "intermezzo", "quietMove", "xRayAttack", "zugzwang"]),
    ("Мат", ["mate", "mateIn1", "mateIn2", "mateIn3", "mateIn4", "mateIn5"]),
    ("Темы мата", ["anastasiaMate", "arabianMate", "backRankMate", "balestraMate", "blindSwineMate", "bodenMate", "cornerMate", "doubleBishopMate", "dovetailMate", "epauletteMate", "hookMate", "killBoxMate", "morphysMate", "operaMate", "pillsburysMate", "swallowstailMate", "triangleMate", "vukovicMate", "smotheredMate"]),
    ("Специальные ходы", ["castling", "enPassant", "promotion", "underPromotion"]),
    ("Цели", ["equality", "advantage", "crushing"]),
    ("Длина", ["oneMove", "short", "long", "veryLong"]),
    ("Источник", ["master", "masterVsMaster", "superGM", "playerGames"]),
]

# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------
CSV_COLUMNS = [
    "PuzzleId", "FEN", "Moves", "Rating", "RatingDeviation",
    "Popularity", "NbPlays", "Themes", "GameUrl", "OpeningTags", "DailyDate",
]

# ---------------------------------------------------------------------------
# Импорт CSV
# ---------------------------------------------------------------------------
IMPORT_BATCH_SIZE = 20_000
IMPORT_PROGRESS_INTERVAL = 25_000

# ---------------------------------------------------------------------------
# Фильтры
# ---------------------------------------------------------------------------
FILTER_DEFAULT_LIMIT = 200
FILTER_PAGE_SIZE = 50
FILTER_DEBOUNCE_MS = 300

# ---------------------------------------------------------------------------
# Миниатюры
# ---------------------------------------------------------------------------
THUMBNAIL_SQUARE_SIZE = 28

# ---------------------------------------------------------------------------
# Сеть
# ---------------------------------------------------------------------------
LICHESS_CDN_TIMEOUT = 15
FETCH_TIMEOUT = 30

# ---------------------------------------------------------------------------
# Окна
# ---------------------------------------------------------------------------
WINDOW_GEOMETRY = "1050x720"
WINDOW_MINSIZE = (900, 600)
PROGRESS_WINDOW_GEOMETRY = "500x140"
DOCX_DIALOG_GEOMETRY = "420x220"
FILTERS_PANEL_WIDTH = 320
SELECTED_PANEL_WIDTH = 305
EXCLUDE_THEMES_LISTBOX_HEIGHT = 6

# ---------------------------------------------------------------------------
# DOCX экспорт
# ---------------------------------------------------------------------------
DOCX_PUZZLES_PER_PAGE = 12
DOCX_IMAGE_WIDTH_EMU = 2000000
DOCX_MARGIN_CM = 1.0
DOCX_TABLE_ROWS = 4
DOCX_TABLE_COLS = 3
DOCX_COL_WIDTH_CM = 6.33
DOCX_ROW_HEIGHT_TWIPS = 2600
DOCX_HEADER_LEFT_COL_WIDTH_CM = 3.5
DOCX_HEADER_RIGHT_COL_WIDTH_CM = 15.0
DOCX_ANSWER_MARGIN_CM = 1.0
DOCX_CAPTION_SPACE_AFTER_PT = 4
DOCX_ANSWER_SPACE_AFTER_PT = 6
DOCX_CELL_MARGIN_TOP_DXA = 0
DOCX_CELL_MARGIN_BOTTOM_DXA = 10
DOCX_CELL_MARGIN_LEFT_DXA = 0
DOCX_CELL_MARGIN_RIGHT_DXA = 0
DOCX_CELL_BORDER_VAL = "nil"
DOCX_CELL_BORDER_SZ = 0
DOCX_PARAGRAPH_SPACE_BEFORE_PT = 2
DOCX_PARAGRAPH_LINE_SPACING_PT = 6

# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------
SQL_CREATE_PUZZLES = """
CREATE TABLE IF NOT EXISTS puzzles (
    PuzzleId TEXT PRIMARY KEY,
    FEN TEXT NOT NULL,
    Moves TEXT NOT NULL,
    Rating INTEGER,
    RatingDeviation INTEGER,
    Popularity INTEGER,
    NbPlays INTEGER,
    Themes TEXT,
    GameUrl TEXT,
    OpeningTags TEXT,
    DailyDate TEXT,
    Color TEXT,
    moves_count INTEGER GENERATED ALWAYS AS ((LENGTH(Moves) - LENGTH(REPLACE(Moves, ' ', '')) + 1) / 2) STORED
);
"""

SQL_CREATE_THEMES = """
CREATE TABLE IF NOT EXISTS puzzle_themes (
    PuzzleId TEXT NOT NULL,
    Theme TEXT NOT NULL,
    FOREIGN KEY (PuzzleId) REFERENCES puzzles (PuzzleId)
);
"""

SQL_CREATE_USER_THEMES = """
CREATE TABLE IF NOT EXISTS user_themes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
"""

SQL_CREATE_USER_PUZZLE_THEMES = """
CREATE TABLE IF NOT EXISTS puzzle_user_themes (
    puzzle_id TEXT NOT NULL,
    theme_id INTEGER NOT NULL,
    PRIMARY KEY (puzzle_id, theme_id),
    FOREIGN KEY (puzzle_id) REFERENCES puzzles (PuzzleId),
    FOREIGN KEY (theme_id) REFERENCES user_themes (id)
);
"""

SQL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_theme ON puzzle_themes(Theme);",
    "CREATE INDEX IF NOT EXISTS idx_rating ON puzzles(Rating);",
    "CREATE INDEX IF NOT EXISTS idx_popularity ON puzzles(Popularity);",
    "CREATE INDEX IF NOT EXISTS idx_nb_plays ON puzzles(NbPlays);",
    "CREATE INDEX IF NOT EXISTS idx_daily_date ON puzzles(DailyDate);",
    "CREATE INDEX IF NOT EXISTS idx_color ON puzzles(Color);",
    "CREATE INDEX IF NOT EXISTS idx_moves_count ON puzzles(moves_count);",
    "CREATE INDEX IF NOT EXISTS idx_color_moves_count ON puzzles(Color, moves_count);",
    "CREATE INDEX IF NOT EXISTS idx_puzzle_themes_theme_puzzle ON puzzle_themes(Theme, PuzzleId);",
    "CREATE INDEX IF NOT EXISTS idx_puzzles_color_rating ON puzzles(Color, Rating DESC);",
    "CREATE INDEX IF NOT EXISTS idx_user_themes_name ON user_themes(name);",
]

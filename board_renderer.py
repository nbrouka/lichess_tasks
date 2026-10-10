"""
Рендеринг шахматной доски в изображение PIL.
Использует предварительно сгенерированные PNG-фигуры из папки pieces/.
"""


from PIL import Image, ImageDraw, ImageFont
import chess

from constants import (
    SQUARE_SIZE, COLOR_LIGHT, COLOR_DARK, PIECE_UNICODE,
    COLOR_COORDINATES, PIECES_DIR, _app_dir,
)

_PIECE_MAP = {
    "P": "wP", "N": "wN", "B": "wB", "R": "wR", "Q": "wQ", "K": "wK",
    "p": "bP", "n": "bN", "b": "bB", "r": "bR", "q": "bQ", "k": "bK",
}

# Кэш подготовленных фигур и шрифтов: чтение PNG и resize с диска при каждом
# рендере стоили ~4 мс на доску (до 32 фигур), теперь берём готовое изображение.
_PIECE_CACHE: dict = {}
_FONT_CACHE: dict = {}


def _load_piece_image(piece_symbol: str, size: int) -> "Image.Image | None":
    """Загружает PNG-фигуру из папки pieces/ (с кэшем по символу и размеру)."""
    cache_key = (piece_symbol, size)
    cached = _PIECE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    piece_name = _PIECE_MAP[piece_symbol]
    png_path = _app_dir() / PIECES_DIR / f"{piece_name}.png"
    img = None
    if png_path.exists():
        img = Image.open(png_path).convert("RGBA")
        if img.size != (size, size):
            img = img.resize((size, size), Image.Resampling.LANCZOS)
    _PIECE_CACHE[cache_key] = img
    return img


def _coord_font(size: int):
    """Шрифт координат с кэшем (truetype грузился с диска на каждый рендер)."""
    cached = _FONT_CACHE.get(("coord", size))
    if cached is None:
        try:
            cached = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size
            )
        except Exception:
            cached = ImageFont.load_default()
        _FONT_CACHE[("coord", size)] = cached
    return cached


def _piece_font(size: int):
    """Шрифт для unicode-фигур (fallback) с кэшем."""
    cached = _FONT_CACHE.get(("piece", size))
    if cached is None:
        try:
            cached = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size
            )
        except Exception:
            cached = ImageFont.load_default()
        _FONT_CACHE[("piece", size)] = cached
    return cached


def render_puzzle(
    fen: str,
    moves: str,
    square_size: int = SQUARE_SIZE,
    use_lichess_pieces: bool = True,
    move_index: int = 0,
    show_coordinates: bool = True,
) -> Image.Image:
    """
    Рендерит позицию задачи в изображение PIL.

    Параметры:
        fen: Начальная позиция FEN.
        moves: Строка ходов решения (UCI, через пробел).
        square_size: Размер клетки в пикселях.
        use_lichess_pieces: Использовать PNG-фигуры из папки pieces/.
        move_index: Индекс хода для отображения позиции после него.
                    0 = начальная позиция, 1 = после первого хода, и т.д.
        show_coordinates: Отображать координаты полей.

    Возвращает:
        Изображение PIL.Image.RGB.
    """
    board = chess.Board(fen)
    move_list = moves.split()
    for i in range(min(move_index, len(move_list))):
        try:
            board.push_uci(move_list[i])
        except ValueError:
            pass

    img = Image.new("RGB", (square_size * 8, square_size * 8), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Клетки доски
    for rank in range(8):
        for file in range(8):
            x1 = file * square_size
            y1 = (7 - rank) * square_size
            x2 = x1 + square_size
            y2 = y1 + square_size
            fill = COLOR_LIGHT if (rank + file) % 2 == 1 else COLOR_DARK
            draw.rectangle([x1, y1, x2, y2], fill=fill)

    # Фигуры
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if not piece:
            continue
        symbol = piece.symbol()
        file_idx = chess.square_file(square)
        rank_idx = chess.square_rank(square)
        x = file_idx * square_size
        y = (7 - rank_idx) * square_size

        if use_lichess_pieces:
            piece_img = _load_piece_image(symbol, square_size)
            if piece_img:
                img.paste(piece_img, (x, y), piece_img)
            else:
                _draw_unicode_piece(draw, symbol, x, y, square_size)
        else:
            _draw_unicode_piece(draw, symbol, x, y, square_size)

    # Координаты
    if show_coordinates:
        coord_font = _coord_font(max(1, int(square_size * 0.25)))

        for i in range(8):
            file_char = chr(ord("a") + i)
            rank_char = str(8 - i)
            draw.text(
                (i * square_size + 4, square_size * 8 - 14),
                file_char,
                font=coord_font,
                fill=COLOR_COORDINATES,
            )
            draw.text(
                (4, i * square_size + 4),
                rank_char,
                font=coord_font,
                fill=COLOR_COORDINATES,
            )

    return img


def _draw_unicode_piece(draw: ImageDraw.ImageDraw, symbol: str, x: int, y: int, size: int) -> None:
    """Отрисовка фигуры юникодом (fallback)."""
    font = _piece_font(max(1, int(size * 0.75)))

    char = PIECE_UNICODE[symbol]
    bbox = draw.textbbox((0, 0), char, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    cx = x + (size - text_width) // 2
    cy = y + (size - text_height) // 2

    outline = "black" if symbol.isupper() else "white"
    main = "white" if symbol.isupper() else "black"

    for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        draw.text((cx + dx, cy + dy), char, font=font, fill=outline)
    draw.text((cx, cy), char, font=font, fill=main)


def save_png(image: Image.Image, path: str) -> None:
    """Сохраняет изображение в PNG."""
    image.save(path, "PNG")

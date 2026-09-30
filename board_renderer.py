"""
Рендеринг шахматной доски в изображение PIL.
Поддерживает два режима: unicode-фигуры и SVG-фигуры с lichess CDN.
"""

import requests
from pathlib import Path
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
import chess
import cairosvg

from constants import (
    SQUARE_SIZE, BOARD_SIZE, COLOR_LIGHT, COLOR_DARK,
    PIECE_UNICODE, COLOR_COORDINATES, LICHESS_CDN_TIMEOUT,
)

_LICHESS_PIECE_BASE = "https://lichess1.org/assets/piece/cburnett"
_PIECE_MAP = {
    "P": "wP", "N": "wN", "B": "wB", "R": "wR", "Q": "wQ", "K": "wK",
    "p": "bP", "n": "bN", "b": "bB", "r": "bR", "q": "bQ", "k": "bK",
}


class PieceSet:
    """Загружает и кэширует SVG-фигуры с lichess CDN."""

    _cache: dict[str, "Image.Image"] = {}

    def __init__(self, cache_dir: str = ".piece_cache", size: int = SQUARE_SIZE):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.size = size

    def get_piece(self, piece_symbol: str) -> "Image.Image":
        key = f"{piece_symbol}_{self.size}"
        if key in PieceSet._cache:
            return PieceSet._cache[key]

        piece_name = _PIECE_MAP[piece_symbol]
        cache_path = self.cache_dir / f"{piece_name}_{self.size}.png"

        if cache_path.exists():
            img = Image.open(cache_path).convert("RGBA")
        else:
            svg_url = f"{_LICHESS_PIECE_BASE}/{piece_name}.svg"
            resp = requests.get(svg_url, timeout=LICHESS_CDN_TIMEOUT)
            resp.raise_for_status()
            png_bytes = cairosvg.svg2png(
                bytestring=resp.content,
                output_width=self.size,
                output_height=self.size,
            )
            img = Image.open(BytesIO(png_bytes)).convert("RGBA")
            img.save(cache_path, "PNG")

        PieceSet._cache[key] = img
        return img


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
        use_lichess_pieces: Использовать SVG-фигуры с lichess CDN.
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

    piece_set = PieceSet(size=square_size) if use_lichess_pieces else None

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

        if piece_set:
            piece_img = piece_set.get_piece(symbol)
            img.paste(piece_img, (x, y), piece_img)
        else:
            _draw_unicode_piece(draw, symbol, x, y, square_size)

    # Координаты
    if show_coordinates:
        try:
            coord_font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                int(square_size * 0.25),
            )
        except Exception:
            coord_font = ImageFont.load_default()

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
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            int(size * 0.75),
        )
    except Exception:
        font = ImageFont.load_default()

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

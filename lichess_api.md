# Получение задач с Lichess.org через API на Python

## Базовая информация

- **Базовый URL**: `https://lichess.org`
- Все запросы идут на `https://lichess.org` (кроме opening explorer — там `explorer.lichess.org`)
- **Rate limiting**: делайте не более одного запроса за раз. При HTTP 429 — уменьшайте частоту запросов.

## Endpoints для задач (puzzles)

### 1. Случайная задача

```
GET /api/puzzle/next
```

Параметры query:
- `angle` — тема или дебют для фильтрации (строка). Доступные темы: https://lichess.org/training/themes
- `color` — `white` | `black` | пусто (автоматически 50% белыми)
- `difficulty` — `easiest` | `easier` | `normal` | `harder` | `hardest` (относительно рейтинга пользователя или 1500 для анонимных)

Аутентификация:
- **Анонимно**: возвращает случайные задачи без персонализации
- **С токеном** (`puzzle:read` scope): возвращает только задачи, которые пользователь ещё не видел

### 2. Задача по ID

```
GET /api/puzzle/{id}
```

Не требует аутентификации.

### 3. Задача дня

```
GET /api/puzzle/daily
```

## Скачивание полной базы задач

Для массового скачивания используйте открытую базу данных:
- https://database.lichess.org/#puzzles
- Файл: `lichess_db_puzzle.csv.zst`
- Формат: CSV с полями `PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl,OpeningTags,DailyDate`

> **Важно**: не используйте `/api/puzzle/next` для массового перебора задач. Используйте полную базу.

## Примеры на Python

### Через `requests`

```python
import requests

BASE_URL = "https://lichess.org"

# 1. Случайная задача (анонимно)
resp = requests.get(f"{BASE_URL}/api/puzzle/next")
resp.raise_for_status()
puzzle = resp.json()
print(puzzle)

# 2. С фильтрами
resp = requests.get(
    f"{BASE_URL}/api/puzzle/next",
    params={"angle": "mate", "difficulty": "harder", "color": "white"}
)
print(resp.json())

# 3. Конкретная задача по ID
puzzle_id = "00008"
resp = requests.get(f"{BASE_URL}/api/puzzle/{puzzle_id}")
print(resp.json())

# 4. Задача дня
resp = requests.get(f"{BASE_URL}/api/puzzle/daily")
print(resp.json())
```

### С авторизацией (Personal Access Token)

1. Создайте токен на https://lichess.org/account/oauth/token
2. Используйте заголовок `Authorization: Bearer {token}`

```python
import requests

TOKEN = "lip_xxxxxxxx"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

resp = requests.get(
    "https://lichess.org/api/puzzle/next",
    headers=HEADERS,
    params={"angle": "fork"}
)
print(resp.json())
```

### Через библиотеку `berserk`

```bash
pip install berserk
```

```python
import berserk

TOKEN = "lip_xxxxxxxx"
session = berserk.TokenSession(TOKEN)
client = berserk.Client(session=session)

# Случайная задача
puzzle = client.puzzles.get_next()
print(puzzle)

# С параметрами
puzzle = client.puzzles.get_next(angle="mate", difficulty="harder", color="white")
print(puzzle)

# По ID
puzzle = client.puzzles.get("00008")
print(puzzle)

# Задача дня
puzzle = client.puzzles.get_daily()
print(puzzle)
```

### Через библиотеку `python-lichess`

```bash
pip install python-lichess
```

```python
import lichess

client = lichess.Client()  # без токена
# или
# client = lichess.Client(token="lip_xxxxxxxx")

puzzle = client.get_puzzle("00008")
print(puzzle)
```

## Формат ответа (PuzzleAndGame)

```json
{
  "game": {
    "id": "abc123",
    "rated": false,
    "variant": "standard",
    "clock": "",
    "daysPerTurn": 0,
    "createdAt": 1234567890000,
    "status": "draw",
    "moves": "e4 e5 Nf3 Nc6 Bc4 Qf6",
    "players": [
      {
        "user": { "id": "player1", "name": "Player One" },
        "color": "white",
        "rating": 1500,
        "ratingDiff": 10
      },
      {
        "user": { "id": "player2", "name": "Player Two" },
        "color": "black",
        "rating": 1500,
        "ratingDiff": -10
      }
    ]
  },
  "puzzle": {
    "id": "00008",
    "rating": 1810,
    "ratingDeviation": 78,
    "popularity": 95,
    "nbPlays": 9527,
    "themes": ["crushing", "hangingPiece", "long", "middlegame"],
    "game": { "id": "abc123" },
    "initialPly": 48,
    "color": "white",
    "fen": "r6k/pp2r2p/4Rp1Q/3p4/8/1N1P2R1/PqP2bPP/7K b - - 0 24",
    "lines": {
      "f2g3": {
        "e6e7": {
          "b2b1": {
            "b3c1": {
              "b1c1": {
                "h6c1": "*"
              }
            }
          }
        }
      }
    }
  }
}
```

## Полезные ссылки

- Официальная документация API: https://lichess.org/api
- OpenAPI спецификация: https://github.com/lichess-org/api/blob/master/doc/specs/lichess-api.yaml
- Berserk docs: https://lichess-org.github.io/berserk/
- Открытая база задач: https://database.lichess.org/#puzzles
- Список тем задач: https://lichess.org/training/themes
- Исходный код тем (lila): https://github.com/ornicar/lila/blob/master/translation/source/puzzleTheme.xml

## Категории тем задач

Темы на Lichess сгруппированы в категории. Полный список и описания доступны на https://lichess.org/training/themes

### Рекомендуемые
- `healthyMix` — Сбалансированная подборка

### Фазы
- `opening` — Дебют
- `middlegame` — Миттельшпиль
- `endgame` — Эндшпиль
- `rookEndgame` — Эндшпиль с ладьями
- `bishopEndgame` — Слоновый эндшпиль
- `pawnEndgame` — Пешечный эндшпиль
- `knightEndgame` — Коневый эндшпиль
- `queenEndgame` — Ферзевый эндшпиль
- `queenRookEndgame` — Ферзь + ладья

### По дебютам
- `sicilianDefense` — Сицилианская защита
- `frenchDefense` — Французская защита
- `queensPawnGame` — Игра ферзевого пешки
- `italianGame` — Итальянская партия
- `carokannDefense` — Защита Каро-Канн
- `scandinavianDefense` — Скандинавская защита
- `queensGambitDeclined` — Отказанный ферзевый гамбит
- `englishOpening` — Английское начало
- `ruyLopez` — Испанская партия
- `scotchGame` — Шотландская партия
- `indianDefense` — Индийская защита
- `philidorDefense` — Защита Филидора

### Мотивы
- `advancedPawn` — Продвинутая пешка
- `attackingF2F7` — Атака на f2/f7
- `capturingDefender` — Захват защитника
- `discoveredAttack` — Открытая атака
- `doubleCheck` — Двойной шах
- `exposedKing` — Открытый король
- `fork` — Вилка
- `hangingPiece` — Висячая фигура
- `kingsideAttack` — Атака на ферзевом фланге
- `pin` — Привязка
- `queensideAttack` — Атака на королевском фланге
- `sacrifice` — Жертва
- `skewer` — Шпиль
- `trappedPiece` — Запертая фигура

### Продвинутые
- `attraction` — Привлечение
- `clearance` — Расчистка
- `collinearMove` — Коллинеарный ход
- `discoveredCheck` — Открытый шах
- `defensiveMove` — Защитительный ход
- `deflection` — Отвлечение
- `interference` — Вмешательство
- `intermezzo` — Интермеццо
- `quietMove` — Тихий ход
- `xRayAttack` — Рентгеновская атака
- `zugzwang` — Цугцванг

### Мат
- `mate` — Мат
- `mateIn1` — Мат в 1
- `mateIn2` — Мат в 2
- `mateIn3` — Мат в 3
- `mateIn4` — Мат в 4
- `mateIn5` — Мат в 5+

### Темы мата
- `anastasiaMate` — Мат Анастасии
- `arabianMate` — Аравийский мат
- `backRankMate` — Мат на последней горизонтали
- `balestraMate` — Мат Балестры
- `blindSwineMate` — Мат «слепой свиньи»
- `bodenMate` — Мат Бодена
- `cornerMate` — Угловой мат
- `doubleBishopMate` — Двойной слоновий мат
- `dovetailMate` — Мат «голубка»
- `epauletteMate` — Мат «эполет»
- `hookMate` — Мат «крючок»
- `killBoxMate` — Мат в «kill box»
- `morphysMate` — Мат Морфи
- `operaMate` — Оперный мат
- `pillsburysMate` — Мат Пиллсбери
- `swallowstailMate` — Мат «хвост ласточки»
- `triangleMate` — Треугольный мат
- `vukovicMate` — Мат Вуковича
- `smotheredMate` — Задушенный мат

### Специальные ходы
- `castling` — Рокировка
- `enPassant` — Взятие на проходе
- `promotion` — Превращение пешки
- `underPromotion` — Превращение в неферзя

### Цели
- `equality` — Равенство
- `advantage` — Преимущество
- `crushing` — Разгромное преимущество

### Длина
- `oneMove` — Однohodovка
- `short` — Короткая
- `long` — Длинная
- `veryLong` — Очень длинная

### Источник
- `master` — Мастерские игры
- `masterVsMaster` — Мастер против мастера
- `superGM` — Супер GM
- `playerGames` — Игры игроков

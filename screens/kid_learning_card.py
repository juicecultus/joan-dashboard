from .shared import *

# ── 19. Kid Learning Card ──────────────────────────────────────────

# Spelling words by difficulty tier
_SPELLING_WORDS = {
    "Easy": ["because", "friend", "people", "thought", "through", "beautiful",
             "different", "important", "together", "favourite"],
    "Medium": ["necessary", "separate", "definitely", "occurrence", "accommodate",
               "embarrass", "conscience", "rhythm", "privilege", "maintenance"],
    "Tricky": ["onomatopoeia", "pneumonia", "psychology", "mischievous",
               "bureaucracy", "entrepreneur", "surveillance", "questionnaire"],
}

# World capitals
_CAPITALS = [
    ("France", "Paris"), ("Japan", "Tokyo"), ("Australia", "Canberra"),
    ("Brazil", "Brasília"), ("Canada", "Ottawa"), ("Egypt", "Cairo"),
    ("Germany", "Berlin"), ("India", "New Delhi"), ("Italy", "Rome"),
    ("Mexico", "Mexico City"), ("Kenya", "Nairobi"), ("Spain", "Madrid"),
    ("Sweden", "Stockholm"), ("Thailand", "Bangkok"), ("Turkey", "Ankara"),
    ("Argentina", "Buenos Aires"), ("South Korea", "Seoul"), ("Poland", "Warsaw"),
    ("Greece", "Athens"), ("Norway", "Oslo"), ("Portugal", "Lisbon"),
    ("China", "Beijing"), ("Russia", "Moscow"), ("Peru", "Lima"),
    ("Ireland", "Dublin"), ("New Zealand", "Wellington"), ("Switzerland", "Bern"),
    ("South Africa", "Pretoria"), ("Colombia", "Bogotá"), ("Vietnam", "Hanoi"),
]


def render_kid_learning_card() -> Image.Image:
    """Rotating learning card for kids — spelling, times tables, capitals, quiz."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    # Rotate mode every 3 minutes (each playlist slot shows a different mode)
    slot = int(time.time() // 180)
    mode = slot % 4

    if mode == 0:
        _draw_spelling_card(draw)
    elif mode == 1:
        _draw_times_table_card(draw)
    elif mode == 2:
        _draw_capitals_card(draw)
    else:
        _draw_quiz_card(draw)

    _dashboard_footer(draw)
    return img


def _draw_spelling_card(draw):
    """Spelling challenge — 6 words to learn and spell."""
    draw.text((WIDTH // 2, 70), "Spelling Bee", fill=0, font=get_font(72, bold=True), anchor="mm")
    draw.text((WIDTH // 2, 130), "Can you spell these words?", fill=120, font=get_font(36), anchor="mm")
    draw.line([(PAD, 170), (WIDTH - PAD, 170)], fill=200, width=2)

    # Pick 6 words seeded by day so they stay consistent
    day_seed = int(datetime.now().strftime("%Y%m%d")) + 100
    rng = random.Random(day_seed)
    tier = rng.choice(list(_SPELLING_WORDS.keys()))
    words = rng.sample(_SPELLING_WORDS[tier], min(6, len(_SPELLING_WORDS[tier])))

    draw.text((WIDTH // 2, 220), f"Level: {tier}", fill=100, font=get_font(40, bold=True), anchor="mm")

    # Two columns of words
    col_x = [WIDTH // 4 + 40, 3 * WIDTH // 4 - 40]
    start_y = 320
    row_h = 120

    for i, word in enumerate(words):
        col = i % 2
        row = i // 2
        x = col_x[col]
        y = start_y + row * row_h

        # Number badge
        draw.ellipse([x - 240, y - 28, x - 190, y + 28], outline=80, width=2)
        draw.text((x - 215, y), str(i + 1), fill=80, font=get_font(36, bold=True), anchor="mm")

        # Word
        word_font = _fit_font_to_width(word, 290, 60, min_size=36)
        draw.text((x - 170, y), _truncate_text(word_font, word, 290), fill=20, font=word_font, anchor="lm")

    # Encouragement
    prompts = ["Write each word 3 times!", "Cover and spell from memory!",
               "Use each word in a sentence!", "Test a family member!"]
    draw.text((WIDTH // 2, HEIGHT - 120), rng.choice(prompts),
              fill=140, font=get_font(36), anchor="mm")


def _draw_times_table_card(draw):
    """Times table practice — one table highlighted with all 12 facts."""
    day_seed = int(datetime.now().strftime("%Y%m%d")) + 200
    rng = random.Random(day_seed)
    table = rng.randint(2, 12)

    draw.text((WIDTH // 2, 70), "Times Tables", fill=0, font=get_font(72, bold=True), anchor="mm")
    draw.text((WIDTH // 2, 140), f"The {table}× Table", fill=60, font=get_font(52), anchor="mm")
    draw.line([(PAD, 185), (WIDTH - PAD, 185)], fill=200, width=2)

    # 12 facts in two columns
    col_x = [WIDTH // 4 + 60, 3 * WIDTH // 4 - 60]
    start_y = 250
    row_h = 80

    for i in range(12):
        col = i % 2
        row = i // 2
        x = col_x[col]
        y = start_y + row * row_h
        n = i + 1

        fact = f"{table} × {n:2d}  =  {table * n}"
        fact_font = _fit_font_to_width(fact, 290, 52, min_size=34)
        draw.text((x, y), fact, fill=20, font=fact_font, anchor="mm")

    # Challenge at bottom
    challenges = [
        f"What is {table} × {rng.randint(13, 20)}?",
        f"How many {table}s make {table * rng.randint(6, 12)}?",
        f"{table} × ? = {table * rng.randint(2, 12)}",
    ]
    draw.line([(PAD + 100, HEIGHT - 180), (WIDTH - PAD - 100, HEIGHT - 180)], fill=200, width=1)
    draw.text((WIDTH // 2, HEIGHT - 120), f"Challenge: {rng.choice(challenges)}",
              fill=80, font=get_font(42, bold=True), anchor="mm")


def _draw_capitals_card(draw):
    """World capitals quiz — 6 countries, can you name the capital?"""
    draw.text((WIDTH // 2, 70), "World Capitals", fill=0, font=get_font(72, bold=True), anchor="mm")
    draw.text((WIDTH // 2, 130), "What is the capital of…?", fill=120, font=get_font(40), anchor="mm")
    draw.line([(PAD, 175), (WIDTH - PAD, 175)], fill=200, width=2)

    day_seed = int(datetime.now().strftime("%Y%m%d")) + 300
    rng = random.Random(day_seed)
    picks = rng.sample(_CAPITALS, 6)

    y = 240
    for i, (country, capital) in enumerate(picks):
        # Country name (question)
        country_font = _fit_font_to_width(f"{i + 1}.  {country}", WIDTH // 2 - PAD - 40, 56, min_size=34)
        draw.text((PAD + 80, y), _truncate_text(country_font, f"{i + 1}.  {country}", WIDTH // 2 - PAD - 40),
                  fill=20, font=country_font, anchor="lm")

        # Answer upside-down style (light grey, smaller)
        cap_font = _fit_font_to_width(capital, WIDTH // 2 - PAD - 60, 40, min_size=24)
        draw.text((WIDTH - PAD - 40, y), _truncate_text(cap_font, capital, WIDTH // 2 - PAD - 60),
                  fill=190, font=cap_font, anchor="rm")

        y += 120

    draw.text((WIDTH // 2, HEIGHT - 120), "Answers in light grey — no peeking!",
              fill=140, font=get_font(32), anchor="mm")


def _draw_quiz_card(draw):
    """Quick quiz — mixed general knowledge for kids."""
    day_seed = int(datetime.now().strftime("%Y%m%d")) + 400
    rng = random.Random(day_seed)

    questions = [
        ("How many sides does a hexagon have?", "6"),
        ("What is the largest planet in our solar system?", "Jupiter"),
        ("How many continents are there?", "7"),
        ("What gas do plants breathe in?", "Carbon dioxide (CO₂)"),
        ("What is the boiling point of water in °C?", "100°C"),
        ("How many bones in the human body?", "206"),
        ("What is the chemical symbol for gold?", "Au"),
        ("Which ocean is the largest?", "Pacific Ocean"),
        ("How many days in a leap year?", "366"),
        ("What is the square root of 144?", "12"),
        ("What colour do you get mixing blue and yellow?", "Green"),
        ("How many minutes in 2 hours?", "120"),
        ("What is the capital of the United Kingdom?", "London"),
        ("How many legs does a spider have?", "8"),
        ("What planet is known as the Red Planet?", "Mars"),
        ("What is 15% of 200?", "30"),
        ("How many teeth does an adult have?", "32"),
        ("What is the longest river in the world?", "The Nile"),
        ("What year did the Titanic sink?", "1912"),
        ("How many strings on a standard guitar?", "6"),
    ]

    picks = rng.sample(questions, 5)

    draw.text((WIDTH // 2, 70), "Quick Quiz", fill=0, font=get_font(72, bold=True), anchor="mm")
    draw.text((WIDTH // 2, 130), "Test your knowledge!", fill=120, font=get_font(40), anchor="mm")
    draw.line([(PAD, 175), (WIDTH - PAD, 175)], fill=200, width=2)

    y = 240
    for i, (q, a) in enumerate(picks):
        # Question
        draw.text((PAD + 40, y), f"Q{i + 1}.", fill=80, font=get_font(44, bold=True), anchor="lm")
        q_font = _fit_font_to_width(q, WIDTH - PAD * 2 - 220, 44, min_size=30)
        draw.text((PAD + 130, y), _truncate_text(q_font, q, WIDTH - PAD * 2 - 220), fill=20, font=q_font, anchor="lm")

        # Answer (very light)
        a_font = _fit_font_to_width(a, WIDTH // 2 - PAD - 40, 34, min_size=22)
        draw.text((WIDTH - PAD - 40, y + 55), _truncate_text(a_font, a, WIDTH // 2 - PAD - 40),
                  fill=190, font=a_font, anchor="rm")

        y += 140

    draw.text((WIDTH // 2, HEIGHT - 120), "Answers in light grey — try first!",
              fill=140, font=get_font(32), anchor="mm")

from .shared import *

# ── 11. Maths Challenge ─────────────────────────────────────────────

def render_maths_challenge() -> Image.Image:
    """Daily maths puzzles for the kids — mix of operations and difficulty."""
    img = Image.new("L", (WIDTH, HEIGHT), 255)
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((WIDTH // 2, 80), "Maths Challenge", fill=0, font=get_font(50, bold=True), anchor="mm")
    draw.text((WIDTH // 2, 130), datetime.now().strftime("%A %d %B"), fill=120, font=get_font(28), anchor="mm")

    # Generate 8 problems of varying difficulty
    problems = []
    # Easy: addition/subtraction
    a, b = random.randint(10, 99), random.randint(10, 99)
    problems.append(f"{a} + {b} = ?")
    a, b = random.randint(30, 99), random.randint(10, 49)
    problems.append(f"{a} − {b} = ?")
    # Medium: multiplication
    a, b = random.randint(3, 12), random.randint(3, 12)
    problems.append(f"{a} × {b} = ?")
    a, b = random.randint(6, 15), random.randint(4, 9)
    problems.append(f"{a} × {b} = ?")
    # Harder: division (ensure clean division)
    b = random.randint(3, 12)
    a = b * random.randint(3, 15)
    problems.append(f"{a} ÷ {b} = ?")
    # Fractions
    n = random.randint(1, 5)
    d = random.choice([2, 3, 4, 5, 8, 10])
    n2 = random.randint(1, 5)
    problems.append(f"{n}/{d} + {n2}/{d} = ?")
    # Percentage
    pct = random.choice([10, 20, 25, 50, 75])
    val = random.choice([40, 60, 80, 100, 120, 200, 500])
    problems.append(f"{pct}% of {val} = ?")
    # Squared
    sq = random.randint(4, 15)
    problems.append(f"{sq}² = ?")

    random.shuffle(problems)

    # One problem, stacked like a classroom exercise; no redundant prompt.
    problem = problems[0].replace(' = ?', '\n= ?')
    return _statement(problem, size=650)

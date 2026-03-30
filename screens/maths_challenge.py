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

    # Draw problems in two centered columns
    col_left = 120
    col_right = 840
    col_text_w = 560
    content_top = 180
    content_bottom = HEIGHT - 160
    row_h = 130
    grid_h = 4 * row_h
    start_y = content_top + max(0, ((content_bottom - content_top) - grid_h) // 2)
    problem_font = _fit_font_to_width("999 × 999 = ?", col_text_w, 80, min_size=64)

    for row in range(4):
        for col in range(2):
            i = row * 2 + col
            problem = problems[i]
            area_x = col_left if col == 0 else col_right
            y = start_y + row * row_h

            # Problem text
            draw.text((area_x, y), _truncate_text(problem_font, problem, col_text_w),
                      fill=20, font=problem_font, anchor="lm")

    # Footer encouragement
    encouragements = [
        "Can you solve them all?", "No calculators allowed!",
        "Show your working!", "Time yourself!",
        "Beat yesterday's time!", "You've got this!",
    ]
    draw.text((WIDTH // 2, HEIGHT - 100), random.choice(encouragements), fill=140, font=get_font(30), anchor="mm")

    _footer(draw, now_str())
    return img

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


def render_kid_learning_card():
    slot = int(time.time() // 1800)
    if slot % 3 == 0:
        words = [w for group in _SPELLING_WORDS.values() for w in group]
        return _statement(words[slot % len(words)], "Cover it. Can you spell it?", size=200)
    if slot % 3 == 1:
        a, b = 2 + slot % 11, 2 + (slot//11) % 11
        return _statement(f"{a} × {b} = ?", "What is the answer?", size=240)
    country, capital = _CAPITALS[slot % len(_CAPITALS)]
    return _statement(capital, "Capital of " + country, size=220)

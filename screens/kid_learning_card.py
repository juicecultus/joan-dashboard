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
    if slot % 2 == 0:
        words = [w for group in _SPELLING_WORDS.values() for w in group]
        img, draw = _canvas()
        # A large pencil makes the spelling activity instantly recognisable.
        pencil = Image.new('L',(1800,400),255)
        pd = ImageDraw.Draw(pencil)
        pd.polygon([(0,0),(1450,0),(1800,200),(1450,400),(0,400)],fill=0)
        pd.rectangle((45,45,1410,355),fill=255)
        pd.line((45,200,1410,200),fill=0,width=24)
        pencil = pencil.rotate(35,expand=True,fillcolor=255,resample=Image.Resampling.BICUBIC)
        from PIL import ImageOps
        pencil = ImageOps.contain(pencil,(1080,780),Image.Resampling.LANCZOS)
        img.paste(pencil,((WIDTH-pencil.width)//2,30))
        _poster_text(draw,words[slot % len(words)],(40,880,1120,400),420)
        _poster_text(draw,'Spell it',(40,1430,1120,110),120,False)
        return img
    country, capital = _CAPITALS[slot % len(_CAPITALS)]
    img, draw = _canvas()
    draw.ellipse((330,40,870,580),fill=0)
    draw.polygon([(355,410),(845,410),(600,800)],fill=0)
    draw.ellipse((475,180,725,430),fill=255)
    _poster_text(draw,capital,(40,880,1120,420),420)
    _poster_text(draw,'Capital of '+country,(40,1420,1120,140),150,False)
    return img

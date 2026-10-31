from .shared import *

# Short paraphrases of Dhammapada verses. Local text avoids the defunct quote API
# and keeps attribution explicit rather than recycling misattributed internet quotes.
_VERSES = [
    ("Hatred is never ended by hatred. It is ended by non-hatred.", "Dhammapada 5 · paraphrase"),
    ("Better than a thousand empty words is one word that brings peace.", "Dhammapada 100 · paraphrase"),
    ("Do no harm. Cultivate what is good. Purify your mind.", "Dhammapada 183 · paraphrase"),
    ("As a solid rock is unmoved by the wind, the wise are unmoved by praise or blame.", "Dhammapada 81 · paraphrase"),
]


def render_buddha_quote():
    text, source = _VERSES[datetime.now().toordinal() % len(_VERSES)]
    return _statement(text, source, size=125, editorial=True)

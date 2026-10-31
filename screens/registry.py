"""Render registry for Joan screens."""

from .daily_agenda import render_daily_agenda
from .quote import render_quote
from .countdown import render_countdown
from .family_photo import render_family_photo
from .word_of_day import render_word_of_day
from .this_day_in_history import render_this_day_in_history
from .art_gallery import render_art_gallery
from .weather_radar import render_weather_radar
from .dad_joke import render_dad_joke
from .year_progress import render_year_progress
from .rss_headlines import render_rss_headlines
from .stock_ticker import render_stock_ticker
from .todo_list import render_todo_list
from .moon_phase import render_moon_phase
from .air_quality import render_air_quality
from .clock_face import render_clock_face
from .upcoming_movies import render_upcoming_movies
from .kid_learning_card import render_kid_learning_card
from .sleep_screen import render_sleep_screen
from .bins import render_bins
from .flip_date import render_flip_date
from .chinese_proverb import render_chinese_proverb
from .bank_holidays import render_bank_holidays
from .flip_clock import render_flip_clock
from .weather_glance import render_weather_glance
from .torah_wisdom import render_torah_wisdom
from .bbc_news import render_bbc_news
from .element_of_day import render_element_of_day
from .github_trending import render_github_trending
from .google_doodle import render_google_doodle
from .trains import render_trains
from .daily_cartoon import render_daily_cartoon
from .literate_movies import render_literate_movies
from .buddha_quote import render_buddha_quote

ALL_SCREENS = {
    "agenda": render_daily_agenda,
    "quote": render_quote,
    "countdown": render_countdown,
    "photo": render_family_photo,
    "word": render_word_of_day,
    "history": render_this_day_in_history,
    "art": render_art_gallery,
    "radar": render_weather_radar,
    "joke": render_dad_joke,
    "progress": render_year_progress,
    "rss": render_rss_headlines,
    "stocks": render_stock_ticker,
    "todo": render_todo_list,
    "moon": render_moon_phase,
    "airquality": render_air_quality,
    "clock": render_clock_face,
    "movies": render_upcoming_movies,
    "learning": render_kid_learning_card,
    "trains": render_trains,
    "bins": render_bins,
    "flipdate": render_flip_date,
    "github": render_github_trending,
    "doodle": render_google_doodle,
    "proverb": render_chinese_proverb,
    "holidays": render_bank_holidays,
    "flipclock": render_flip_clock,
    "weatherglance": render_weather_glance,
    "torah": render_torah_wisdom,
    "bbc": render_bbc_news,
    "element": render_element_of_day,
    "cartoon": render_daily_cartoon,
    "litmovies": render_literate_movies,
    "buddha": render_buddha_quote,
}

__all__ = [
    "render_daily_agenda",
    "render_quote",
    "render_countdown",
    "render_family_photo",
    "render_word_of_day",
    "render_this_day_in_history",
    "render_art_gallery",
    "render_weather_radar",
    "render_dad_joke",
    "render_year_progress",
    "render_rss_headlines",
    "render_stock_ticker",
    "render_todo_list",
    "render_moon_phase",
    "render_air_quality",
    "render_clock_face",
    "render_upcoming_movies",
    "render_kid_learning_card",
    "render_sleep_screen",
    "render_bins",
    "render_flip_date",
    "render_chinese_proverb",
    "render_bank_holidays",
    "render_flip_clock",
    "render_weather_glance",
    "render_torah_wisdom",
    "render_bbc_news",
    "render_element_of_day",
    "render_github_trending",
    "render_google_doodle",
    "render_trains",
    "render_daily_cartoon",
    "render_literate_movies",
    "render_buddha_quote",
    "ALL_SCREENS",
]

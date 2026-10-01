"""Configuration for the Academic Study Bot."""
import os
from pathlib import Path

# Load environment from .env file
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

BASE_DIR = Path("/root/study_bot")
DB_PATH = str(BASE_DIR / "study.db")
MATERIALS_DIR = str(BASE_DIR / "materials")

# Local inference API
INFERENCE_API_URL = "http://127.0.0.1:20128/v1"
INFERENCE_API_KEY = os.environ.get("INFERENCE_API_KEY", "")

# University timetable PDF (FLSH Mohammedia S5-G2)
TIMETABLE_URL = "http://flshm.univh2c.ma/data-ng-x2021/emploi/data/EN/SM05GR02.pdf"

# Telegram
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# GitHub Pages mini-app URL
WEBAPP_URL = "https://kaine28rin-eng.github.io/Studex33io-web/"

# Modules (your 5 actual courses)
MODULES = {
    "19th Century Literature": {
        "thread_id": None,
        "description": "19th Century Russian & British Literature",
        "materials_subdir": "19th_century_lit",
        "classroom_code": None,
        "classroom_url": None,
    },
    "Cultural Studies": {
        "thread_id": None,
        "description": "Cultural theory, film, media studies",
        "materials_subdir": "cultural_studies",
        "classroom_code": "f4sls4cj",
        "classroom_url": "https://classroom.google.com/c/f4sls4cj",
    },
    "Applied Linguistics": {
        "thread_id": None,
        "description": "Applied Linguistics and terminology",
        "materials_subdir": "applied_linguistics",
        "classroom_code": None,
        "classroom_url": None,
    },
    "Advanced Research Techniques": {
        "thread_id": None,
        "description": "Advanced research methodologies",
        "materials_subdir": "advanced_research",
        "classroom_code": "pzsjcbpu",
        "classroom_url": "https://classroom.google.com/c/pzsjcbpu",
    },
    "General Linguistics": {
        "thread_id": None,
        "description": "Foundational linguistics concepts and general linguistics",
        "materials_subdir": "general_linguistics",
        "classroom_code": None,
        "classroom_url": None,
    },
}

# Spaced repetition intervals (in days)
SPACED_REPETITION_INTERVALS = [0.25, 1, 3, 7, 14, 30]

# Active recall session defaults
ACTIVE_RECALL_DURATION_MINUTES = 25

# Group chat where the bot operates
GROUP_CHAT_ID = os.environ.get("GROUP_CHAT_ID", "")

# Admin user IDs (only these users can upload/inject data)
ADMIN_USER_IDS = {5852460298}


def is_admin(user_id: int) -> bool:
    """Check if a user is an admin (can upload/inject materials)."""
    return user_id in ADMIN_USER_IDS


# Weekly timetable (FLSH Mohammedia S5-G02, autumn 2026/2027)
TIMETABLE = {
    "Monday": [],
    "Tuesday": [
        "10:30-12:30 | 19th Century Literature (Poetry, drama, fiction) | Salle 10 | EL MAJDOUBI",
        "12:30-14:30 | General Linguistics | Salle 01 | EL HILALI",
    ],
    "Wednesday": [
        "14:30-16:30 | Cultural Studies | Amphi 3 | FROUNI",
    ],
    "Thursday": [
        "10:30-12:30 | Advanced Research Techniques | Salle 01 | TABZA",
    ],
    "Friday": [],
    "Saturday": [],
}

# Upcoming deadlines (dummy data — edit with your actual S5 exams/assignments)
DEADLINES = [
    {
        "due_date": "2026-10-15",
        "title": "Cultural Studies Essay Draft",
        "description": "Submit first draft of postcolonial theory essay",
        "module": "Cultural Studies",
    },
    {
        "due_date": "2026-10-22",
        "title": "Advanced Research Techniques Quiz",
        "description": "SM-2 spaced repetition methodology quiz",
        "module": "Advanced Research Techniques",
    },
    {
        "due_date": "2026-11-05",
        "title": "19th Century Literature Midterm",
        "description": "Midterm exam covering Romantic poets",
        "module": "19th Century Literature",
    },
]
"""Manual-first evaluation helpers. Never invent grades."""
from __future__ import annotations
import json
from pathlib import Path
QUESTIONS=Path(__file__).with_name('questions.json')
def load_questions(): return json.loads(QUESTIONS.read_text(encoding='utf-8'))
def grade_refusal(question:dict, refused:bool)->str:
    if question['type']=='unanswerable': return 'refused_correctly' if refused else 'wrong'
    return 'refused_wrongly' if refused else 'correct'  # answerable factual review remains manual

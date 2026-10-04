import json
from pathlib import Path

from cpu_jev.types import Option, SelectRequest, YesNoRequest

_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def load(label: str) -> SelectRequest | YesNoRequest:
    if label == "decide":
        return _choice(_read("decide.json"))
    if label == "yes_no":
        return _noul(_read("yes_no.json"))
    raise ValueError(f"unknown fixture label {label!r}")


def _read(name: str) -> dict:
    path = _DIR / name
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must be a JSON object")
    if "state" not in payload or "questions" not in payload:
        raise ValueError(f"{name} must include state and questions")
    return payload


def _choice(payload: dict) -> SelectRequest:
    question = _one_question(payload, "choice")
    criteria = question.get("criteria")
    if not isinstance(criteria, dict) or len(criteria) < 2:
        raise ValueError("choice criteria must map at least two options")
    options: list[Option] = []
    for option_id, label in criteria.items():
        if not isinstance(option_id, str):
            raise ValueError("criteria ids must be strings")
        if not isinstance(label, str):
            raise ValueError("criteria labels must be strings")
        options.append(Option(option_id, label))
    return SelectRequest(_state(payload["state"]), _instructions(question), tuple(options))


def _noul(payload: dict) -> YesNoRequest:
    question = _one_question(payload, "noul")
    if "criteria" in question:
        raise ValueError("noul questions have no criteria")
    return YesNoRequest(_state(payload["state"]), _instructions(question))


def _one_question(payload: dict, expected: str) -> dict:
    questions = payload["questions"]
    if not isinstance(questions, dict) or len(questions) != 1:
        raise ValueError("fixture must contain one question")
    name, question = next(iter(questions.items()))
    if not isinstance(name, str) or name.strip() == "":
        raise ValueError("question name must be a non-empty string")
    if not isinstance(question, dict):
        raise ValueError("question must be an object")
    if question.get("type") != expected:
        raise ValueError(f"question type must be {expected}")
    return question


def _instructions(question: dict) -> str:
    text = question.get("instructions")
    if not isinstance(text, str) or text.strip() == "":
        raise ValueError("instructions must be a non-empty string")
    return text


def _state(value: object) -> str | dict | list:
    if isinstance(value, (str, dict, list)):
        return value
    raise ValueError("state must be a string, dict, or list")

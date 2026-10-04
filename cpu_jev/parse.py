import re

from cpu_jev.types import (
    ParseError,
    SelectDecision,
    SelectRequest,
    YesNoDecision,
    YesNoRequest,
)

_THINK = re.compile(r"<think>(.*?)</think>", re.DOTALL)
_YES_NO = ("yes", "no")
_CHOICE_LEAD = re.compile(r"(?<!\w)(?:be|is|are|pick|choose|select)\s+", re.IGNORECASE)


def parse_select(request: SelectRequest, completion: str) -> SelectDecision:
    reasoning, answer = _split_think(completion)
    allowed = tuple(option.id for option in request.options)
    pick = _choose_select(answer, allowed)
    return SelectDecision(kind="select", pick=pick, reasoning=reasoning)


def parse_yes_no(request: YesNoRequest, completion: str) -> YesNoDecision:
    reasoning, answer = _split_think(completion)
    pick = _choose(answer, _YES_NO, fold=True)
    return YesNoDecision(kind="yes_no", pick=pick, reasoning=reasoning)


def _split_think(completion: str) -> tuple[str, str]:
    if not isinstance(completion, str):
        raise ParseError("completion must be a string")
    match = _THINK.search(completion)
    if match is None:
        raise ParseError("completion is missing a think block")
    return match.group(1).strip(), completion[match.end() :]


def _choose(answer: str, allowed: tuple[str, ...], *, fold: bool) -> str:
    exact = _unique(_exact_line_hits(answer, allowed, fold=fold))
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ParseError("pick matched more than one option")
    words = _unique(_whole_word_hits(answer, allowed, fold=fold))
    if len(words) == 1:
        return words[0]
    if len(words) > 1:
        raise ParseError("pick matched more than one option")
    raise ParseError("pick is missing or not allowed")


def _choose_select(answer: str, allowed: tuple[str, ...]) -> str:
    exact = _exact_line_hits(answer, allowed, fold=False)
    if exact:
        return exact[-1]
    stated = _stated_ids(answer, allowed)
    if stated:
        return stated[-1]
    words = _whole_word_hits(answer, allowed, fold=False)
    if words:
        return words[-1]
    raise ParseError("pick is missing or not allowed")


def _stated_ids(answer: str, allowed: tuple[str, ...]) -> list[str]:
    allowed_set = set(allowed)
    found: list[str] = []
    for match in _CHOICE_LEAD.finditer(answer):
        token_match = re.match(r"\w+", answer[match.end() :])
        if token_match is None:
            continue
        token = token_match.group(0)
        if token in allowed_set:
            found.append(token)
    return found


def _exact_line_hits(answer: str, allowed: tuple[str, ...], *, fold: bool) -> list[str]:
    index: dict[str, str] = {}
    for item in allowed:
        index.setdefault(item.casefold() if fold else item, item)
    found: list[str] = []
    for line in answer.splitlines():
        token = line.strip()
        key = token.casefold() if fold else token
        item = index.get(key)
        if item is not None:
            found.append(item)
    return found


def _whole_word_hits(answer: str, allowed: tuple[str, ...], *, fold: bool) -> list[str]:
    if not allowed:
        return []
    index: dict[str, str] = {}
    for item in allowed:
        index.setdefault(item.casefold() if fold else item, item)
    pattern = "|".join(re.escape(item) for item in sorted(allowed, key=len, reverse=True))
    flags = re.IGNORECASE if fold else 0
    found: list[str] = []
    for match in re.finditer(rf"(?<!\w)({pattern})(?!\w)", answer, flags):
        key = match.group(1).casefold() if fold else match.group(1)
        item = index.get(key)
        if item is not None:
            found.append(item)
    return found


def _unique(items: list[str]) -> list[str]:
    found: list[str] = []
    for item in items:
        if item not in found:
            found.append(item)
    return found

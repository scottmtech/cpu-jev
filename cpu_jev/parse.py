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


def parse_select(request: SelectRequest, completion: str) -> SelectDecision:
    reasoning, answer = _split_think(completion)
    allowed = tuple(option.id for option in request.options)
    pick = _choose(answer, allowed, fold=False)
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
    exact = _exact_lines(answer, allowed, fold=fold)
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ParseError("pick matched more than one option")
    words = _whole_words(answer, allowed, fold=fold)
    if len(words) == 1:
        return words[0]
    if len(words) > 1:
        raise ParseError("pick matched more than one option")
    raise ParseError("pick is missing or not allowed")


def _exact_lines(answer: str, allowed: tuple[str, ...], *, fold: bool) -> list[str]:
    index: dict[str, str] = {}
    for item in allowed:
        index.setdefault(item.casefold() if fold else item, item)
    found: list[str] = []
    for line in answer.splitlines():
        token = line.strip()
        key = token.casefold() if fold else token
        item = index.get(key)
        if item is not None and item not in found:
            found.append(item)
    return found


def _whole_words(answer: str, allowed: tuple[str, ...], *, fold: bool) -> list[str]:
    flags = re.IGNORECASE if fold else 0
    found: list[str] = []
    for item in allowed:
        pattern = rf"(?<!\w){re.escape(item)}(?!\w)"
        if re.search(pattern, answer, flags):
            found.append(item)
    return found

from collections.abc import Callable

from cpu_jev.parse import parse_select, parse_yes_no
from cpu_jev.prompt import render_select, render_yes_no
from cpu_jev.types import (
    ParseError,
    SelectDecision,
    SelectRequest,
    YesNoDecision,
    YesNoRequest,
)

Complete = Callable[[str], str]

__all__ = [
    "select",
    "yes_no",
    "select_decision",
    "yes_no_decision",
]


def select(
    request: SelectRequest,
    complete: Complete | None = None,
) -> SelectDecision:
    if not isinstance(request, SelectRequest):
        raise TypeError("request must be a SelectRequest")
    if complete is None:
        from cpu_jev.runner import select as run_select

        return run_select(request)
    return select_decision(request, _completion(complete, render_select(request)))


def yes_no(
    request: YesNoRequest,
    complete: Complete | None = None,
) -> YesNoDecision:
    if not isinstance(request, YesNoRequest):
        raise TypeError("request must be a YesNoRequest")
    if complete is None:
        from cpu_jev.runner import yes_no as run_yes_no

        return run_yes_no(request)
    return yes_no_decision(request, _completion(complete, render_yes_no(request)))


def select_decision(request: SelectRequest, completion: str) -> SelectDecision:
    if not isinstance(request, SelectRequest):
        raise TypeError("request must be a SelectRequest")
    return parse_select(request, completion)


def yes_no_decision(request: YesNoRequest, completion: str) -> YesNoDecision:
    if not isinstance(request, YesNoRequest):
        raise TypeError("request must be a YesNoRequest")
    return parse_yes_no(request, completion)


def _completion(complete: Complete, prompt: str) -> str:
    if not callable(complete):
        raise TypeError("complete must be a callable")
    completion = complete(prompt)
    if not isinstance(completion, str):
        raise ParseError("completion must be a string")
    return completion

from dataclasses import dataclass
from typing import Literal

State = str | dict | list


class ParseError(Exception):
    pass


def _non_empty(value: object, name: str) -> None:
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"{name} must be a non-empty string")


def _state(value: object) -> None:
    if not isinstance(value, (str, dict, list)):
        raise ValueError("state must be a string, dict, or list")


@dataclass(frozen=True, slots=True)
class Option:
    id: str
    label: str

    def __post_init__(self) -> None:
        _non_empty(self.id, "option id")
        if not isinstance(self.label, str):
            raise TypeError("option label must be a string")


@dataclass(frozen=True, slots=True)
class SelectRequest:
    state: State
    instructions: str
    options: tuple[Option, ...]

    def __post_init__(self) -> None:
        _state(self.state)
        _non_empty(self.instructions, "instructions")
        if not isinstance(self.options, tuple):
            raise TypeError("options must be a tuple")
        if len(self.options) < 2:
            raise ValueError("select request needs at least two options")
        seen: set[str] = set()
        for option in self.options:
            if not isinstance(option, Option):
                raise TypeError("options must contain Option values")
            if option.id in seen:
                raise ValueError("option ids must be unique")
            seen.add(option.id)


@dataclass(frozen=True, slots=True)
class YesNoRequest:
    state: State
    instructions: str

    def __post_init__(self) -> None:
        _state(self.state)
        _non_empty(self.instructions, "instructions")


@dataclass(frozen=True, slots=True)
class SelectDecision:
    kind: Literal["select"]
    pick: str
    reasoning: str

    def __post_init__(self) -> None:
        if self.kind != "select":
            raise ValueError("kind must be select")
        _non_empty(self.pick, "pick")
        if not isinstance(self.reasoning, str):
            raise TypeError("reasoning must be a string")


@dataclass(frozen=True, slots=True)
class YesNoDecision:
    kind: Literal["yes_no"]
    pick: Literal["yes", "no"]
    reasoning: str

    def __post_init__(self) -> None:
        if self.kind != "yes_no":
            raise ValueError("kind must be yes_no")
        if self.pick not in ("yes", "no"):
            raise ValueError("pick must be yes or no")
        if not isinstance(self.reasoning, str):
            raise TypeError("reasoning must be a string")

import json

from cpu_jev.types import SelectRequest, YesNoRequest


def render_select(request: SelectRequest) -> str:
    option_lines = [f"{option.id}: {option.label}" for option in request.options]
    return _render(
        request.state,
        request.instructions,
        option_lines,
        "Then write only the option id.",
    )


def render_yes_no(request: YesNoRequest) -> str:
    return _render(
        request.state,
        request.instructions,
        [],
        "Then write only yes or no.",
    )


def _render(
    state: str | dict | list,
    instructions: str,
    option_lines: list[str],
    closing: str,
) -> str:
    lines = [
        "/think",
        "State:",
        _render_state(state),
        "",
        "Instructions:",
        instructions,
    ]
    if option_lines:
        lines.extend(["", "Options:", *option_lines])
    lines.extend(
        [
            "",
            "Write at most three short sentences in the think block.",
            closing,
        ]
    )
    return "\n".join(lines)


def _render_state(state: str | dict | list) -> str:
    if isinstance(state, str):
        return state
    return json.dumps(state)

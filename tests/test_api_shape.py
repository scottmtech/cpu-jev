import unittest

from cpu_jev import (
    Option,
    SelectRequest,
    YesNoRequest,
    select,
    yes_no,
)


def _route() -> SelectRequest:
    return SelectRequest(
        state="Customer: I was charged twice and nobody has replied for 3 days.",
        instructions="Where should this go?",
        options=(
            Option("billing", "money"),
            Option("bug", "broken"),
            Option("account", "login"),
        ),
    )


def _gate() -> YesNoRequest:
    return YesNoRequest(
        state="Customer: I was charged twice and nobody has replied for 3 days.",
        instructions="Escalate to a human now?",
    )


class TestApiShape(unittest.TestCase):
    def test_select_returns_literal_pick_and_think_body(self) -> None:
        seen: dict[str, str] = {}

        def complete(prompt: str) -> str:
            seen["prompt"] = prompt
            return "<think>charged twice, so billing.</think>\nbilling"

        decision = select(_route(), complete=complete)
        self.assertEqual(decision.kind, "select")
        self.assertEqual(decision.pick, "billing")
        self.assertEqual(decision.reasoning, "charged twice, so billing.")
        self.assertIn(decision.pick, ("billing", "bug", "account"))
        self.assertIn("/think", seen["prompt"])
        self.assertNotIn(decision.reasoning, seen["prompt"])

    def test_yes_no_returns_literal_pick_and_think_body(self) -> None:
        seen: dict[str, str] = {}

        def complete(prompt: str) -> str:
            seen["prompt"] = prompt
            return "<think>nobody has replied.</think>\nyes"

        decision = yes_no(_gate(), complete=complete)
        self.assertEqual(decision.kind, "yes_no")
        self.assertEqual(decision.pick, "yes")
        self.assertEqual(decision.reasoning, "nobody has replied.")
        self.assertIn(decision.pick, ("yes", "no"))
        self.assertIn("/think", seen["prompt"])
        self.assertNotIn(decision.reasoning, seen["prompt"])

    def test_select_prompt_renders_dict_state_as_json(self) -> None:
        seen: dict[str, str] = {}

        def complete(prompt: str) -> str:
            seen["prompt"] = prompt
            return "<think>ticket is open.</think>\nbilling"

        request = SelectRequest(
            state={"ticket": "t-1"},
            instructions="Where should this go?",
            options=_route().options,
        )
        decision = select(request, complete=complete)
        self.assertEqual(decision.pick, "billing")
        self.assertEqual(decision.reasoning, "ticket is open.")
        prompt = seen["prompt"]
        self.assertIn("/think", prompt)
        self.assertIn('{"ticket": "t-1"}', prompt)
        self.assertIn("Where should this go?", prompt)
        self.assertIn("billing: money", prompt)
        self.assertNotIn(decision.reasoning, prompt)

    def test_select_prompt_renders_list_state_as_json(self) -> None:
        seen: dict[str, str] = {}

        def complete(prompt: str) -> str:
            seen["prompt"] = prompt
            return "<think>two notes.</think>\naccount"

        request = SelectRequest(
            state=["charged twice", "no reply"],
            instructions="Where should this go?",
            options=_route().options,
        )
        decision = select(request, complete=complete)
        self.assertEqual(decision.pick, "account")
        self.assertEqual(decision.reasoning, "two notes.")
        self.assertIn('["charged twice", "no reply"]', seen["prompt"])
        self.assertNotIn(decision.reasoning, seen["prompt"])

    def test_yes_no_prompt_keeps_string_state(self) -> None:
        seen: dict[str, str] = {}

        def complete(prompt: str) -> str:
            seen["prompt"] = prompt
            return "<think>still waiting.</think>\nno"

        request = _gate()
        decision = yes_no(request, complete=complete)
        self.assertEqual(decision.pick, "no")
        self.assertEqual(decision.reasoning, "still waiting.")
        prompt = seen["prompt"]
        self.assertIn("\n" + request.state + "\n", "\n" + prompt + "\n")
        self.assertIn("Escalate to a human now?", prompt)

    def test_empty_option_id_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Option("", "money")
        with self.assertRaises(ValueError):
            Option("   ", "money")

    def test_select_rejects_duplicate_and_single_options(self) -> None:
        with self.assertRaises(ValueError):
            SelectRequest(
                "state",
                "Where should this go?",
                (Option("billing", "money"), Option("billing", "again")),
            )
        with self.assertRaises(ValueError):
            SelectRequest("state", "Where should this go?", (Option("billing", "money"),))

    def test_empty_instructions_and_bad_state_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            YesNoRequest("state", "  ")
        with self.assertRaises(ValueError):
            YesNoRequest(3, "Escalate to a human now?")

import unittest

from cpu_jev import SelectRequest, YesNoRequest, select, yes_no
from cpu_jev.fixtures import load


class TestFixtures(unittest.TestCase):
    def test_decide_maps_published_choice_and_selects(self) -> None:
        request = load("decide")
        self.assertIsInstance(request, SelectRequest)
        self.assertEqual(
            request.state,
            "Customer: I was charged twice and nobody has replied for 3 days.",
        )
        self.assertEqual(request.instructions, "Where should this go?")
        self.assertEqual(
            tuple(option.id for option in request.options),
            ("billing", "bug", "account"),
        )
        self.assertEqual(
            tuple(option.label for option in request.options),
            ("money", "broken", "login"),
        )
        seen: dict[str, str] = {}

        def complete(prompt: str) -> str:
            seen["prompt"] = prompt
            return "<think>money left twice.</think>\nbilling"

        decision = select(request, complete=complete)
        self.assertEqual(decision.kind, "select")
        self.assertEqual(decision.pick, "billing")
        self.assertEqual(decision.reasoning, "money left twice.")
        self.assertIn("/think", seen["prompt"])
        self.assertIn(request.state, seen["prompt"])
        self.assertIn("billing: money", seen["prompt"])
        self.assertNotIn(decision.reasoning, seen["prompt"])

    def test_yes_no_maps_published_noul_and_answers(self) -> None:
        request = load("yes_no")
        self.assertIsInstance(request, YesNoRequest)
        self.assertEqual(
            request.state,
            "Customer: I was charged twice and nobody has replied for 3 days.",
        )
        self.assertEqual(request.instructions, "Escalate to a human now?")
        seen: dict[str, str] = {}

        def complete(prompt: str) -> str:
            seen["prompt"] = prompt
            return "<think>three days without a reply.</think>\nno"

        decision = yes_no(request, complete=complete)
        self.assertEqual(decision.kind, "yes_no")
        self.assertEqual(decision.pick, "no")
        self.assertEqual(decision.reasoning, "three days without a reply.")
        self.assertIn("/think", seen["prompt"])
        self.assertIn("Escalate to a human now?", seen["prompt"])
        self.assertNotIn(decision.reasoning, seen["prompt"])

    def test_unknown_fixture_label_raises(self) -> None:
        with self.assertRaises(ValueError):
            load("scores")

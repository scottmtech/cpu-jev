import unittest

from cpu_jev import Option, SelectRequest, select


def _cpu_ready() -> bool:
    from cpu_jev.runner import available

    return available()


class TestCpuLive(unittest.TestCase):
    @unittest.skipUnless(
        _cpu_ready(),
        "Qwen3-0.6B-Q8_0.gguf and llama.cpp are not present",
    )
    def test_real_select_pick_is_declared_and_think_is_nonempty(self) -> None:
        request = SelectRequest(
            state="Customer: I was charged twice and nobody has replied for 3 days.",
            instructions="Where should this go?",
            options=(
                Option("billing", "money"),
                Option("bug", "broken"),
                Option("account", "login"),
            ),
        )
        decision = select(request)
        self.assertEqual(decision.kind, "select")
        self.assertIn(decision.pick, ("billing", "bug", "account"))
        self.assertNotEqual(decision.reasoning.strip(), "")
        self.assertNotIn("<think>", decision.reasoning)
        self.assertNotIn("</think>", decision.reasoning)

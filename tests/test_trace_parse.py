import unittest

from cpu_jev import (
    Option,
    ParseError,
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


class TestTraceParse(unittest.TestCase):
    def test_think_after_cli_preamble(self) -> None:
        decision = select(
            _route(),
            complete=lambda _prompt: (
                "Loading model...\n"
                "> /think\n"
                "<think>charged twice, so billing.</think>\n"
                "billing\n"
                "Exiting...\n"
            ),
        )
        self.assertEqual(decision.pick, "billing")
        self.assertEqual(decision.reasoning, "charged twice, so billing.")

    def test_exact_option_line_and_think_body(self) -> None:
        decision = select(
            _route(),
            complete=lambda _prompt: "<think>\nmoney left the account twice.\n</think>\nbilling\n",
        )
        self.assertEqual(decision.pick, "billing")
        self.assertEqual(decision.reasoning, "money left the account twice.")

    def test_missing_think_raises(self) -> None:
        with self.assertRaises(ParseError):
            select(_route(), complete=lambda _prompt: "billing")

    def test_unclosed_think_raises(self) -> None:
        with self.assertRaises(ParseError):
            select(_route(), complete=lambda _prompt: "<think>still going\nbilling")

    def test_pick_not_in_options_raises(self) -> None:
        with self.assertRaises(ParseError):
            select(
                _route(),
                complete=lambda _prompt: "<think>refund is closer.</think>\nrefund",
            )

    def test_extra_prose_uses_whole_word_id(self) -> None:
        decision = select(
            _route(),
            complete=lambda _prompt: "<think>the charge is the issue.</think>\nThe route is billing.",
        )
        self.assertEqual(decision.pick, "billing")
        self.assertEqual(decision.reasoning, "the charge is the issue.")

    def test_exact_line_beats_other_id_in_prose(self) -> None:
        text = (
            "<think>billing was mentioned but the break is the product.</think>\n"
            "billing might fit\n"
            "bug"
        )
        decision = select(_route(), complete=lambda _prompt: text)
        self.assertEqual(decision.pick, "bug")
        self.assertEqual(
            decision.reasoning,
            "billing was mentioned but the break is the product.",
        )

    def test_last_exact_line_is_the_pick(self) -> None:
        decision = select(
            _route(),
            complete=lambda _prompt: "<think>split.</think>\nbilling\nbug",
        )
        self.assertEqual(decision.pick, "bug")
        self.assertEqual(decision.reasoning, "split.")

    def test_option_id_case_must_match(self) -> None:
        with self.assertRaises(ParseError):
            select(_route(), complete=lambda _prompt: "<think>capitalized.</think>\nBilling")

    def test_last_declared_id_in_prose_is_the_pick(self) -> None:
        decision = select(
            _route(),
            complete=lambda _prompt: "<think>unsure.</think>\nbilling or bug",
        )
        self.assertEqual(decision.pick, "bug")
        self.assertEqual(decision.reasoning, "unsure.")

    def test_echoed_option_list_then_stated_choice(self) -> None:
        request = SelectRequest(
            state="I upgraded to Pro yesterday but the dashboard still says Free and I got charged. Which one is it?",
            instructions="Which team should handle this ticket?",
            options=(
                Option("billing", "Charges, invoices, and refunds"),
                Option("technical", "Bugs, outages, and broken features"),
                Option("account", "Login, password, and profile changes"),
            ),
        )
        completion = (
            "<think>\n"
            "Okay, let's see. The user said they upgraded to Pro yesterday but the dashboard still says Free and they got charged. The question is which team to handle this ticket.\n"
            "\n"
            "First, I need to understand the issue. Upgrading to Pro means they changed their account type, right? But if the dashboard shows Free</think>\n"
            "\n"
            "option: billing: Charges, invoices, and refunds\n"
            "technical: Bugs, outages, and broken features\n"
            "account: Login, password, and profile changes\n"
            "\n"
            "The user upgraded to Pro but the dashboard is still Free. That suggests there might be a conflict between their account change (Pro) and the current status (Free). The charges being made might indicate that the system still has invoices or unresolved issues. \n"
            "\n"
            "Since the problem is about the billing or charges being affected, the correct team would be billing. But I need to check if the technical team can handle it. If there's a bug related to the dashboard not reflecting\n"
        )
        decision = select(request, complete=lambda _prompt: completion)
        self.assertEqual(decision.pick, "billing")
        self.assertEqual(
            decision.reasoning,
            "Okay, let's see. The user said they upgraded to Pro yesterday but the dashboard still says Free and they got charged. The question is which team to handle this ticket.\n"
            "\n"
            "First, I need to understand the issue. Upgrading to Pro means they changed their account type, right? But if the dashboard shows Free",
        )

    def test_lookalike_word_is_not_a_pick(self) -> None:
        with self.assertRaises(ParseError):
            select(
                _route(),
                complete=lambda _prompt: "<think>the product failed.</think>\nThis is not a debug task.",
            )

    def test_id_inside_think_is_not_the_pick(self) -> None:
        with self.assertRaises(ParseError):
            select(
                _route(),
                complete=lambda _prompt: "<think>billing is the only word here.</think>\nno declared id in the answer",
            )

    def test_yes_exact_line_is_case_insensitive(self) -> None:
        decision = yes_no(
            _gate(),
            complete=lambda _prompt: "<think>still unanswered.</think>\nYes",
        )
        self.assertEqual(decision.kind, "yes_no")
        self.assertEqual(decision.pick, "yes")
        self.assertEqual(decision.reasoning, "still unanswered.")

    def test_yes_no_prose_uses_whole_word(self) -> None:
        decision = yes_no(
            _gate(),
            complete=lambda _prompt: "<think>three days of silence.</think>\nEscalate, yes.",
        )
        self.assertEqual(decision.pick, "yes")
        self.assertEqual(decision.reasoning, "three days of silence.")

    def test_exact_yes_line_beats_no_word(self) -> None:
        decision = yes_no(
            _gate(),
            complete=lambda _prompt: "<think>check the queue.</think>\nno way\nyes",
        )
        self.assertEqual(decision.pick, "yes")
        self.assertEqual(decision.reasoning, "check the queue.")

    def test_both_yes_and_no_in_prose_raise(self) -> None:
        with self.assertRaises(ParseError):
            yes_no(
                _gate(),
                complete=lambda _prompt: "<think>unsure.</think>\nyes but also no",
            )

    def test_nobody_and_yesterday_are_not_answers(self) -> None:
        with self.assertRaises(ParseError):
            yes_no(
                _gate(),
                complete=lambda _prompt: "<think>waiting.</think>\nnobody replied yesterday",
            )

    def test_yes_inside_think_is_not_the_pick(self) -> None:
        with self.assertRaises(ParseError):
            yes_no(
                _gate(),
                complete=lambda _prompt: "<think>yes</think>\nmaybe later",
            )

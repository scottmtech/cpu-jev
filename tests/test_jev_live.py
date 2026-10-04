import json
import os
import unittest
from pathlib import Path
from unittest import mock

from cpu_jev.jev_live import decide

_ROOT = Path(__file__).resolve().parents[1]


class TestJevLive(unittest.TestCase):
    def test_no_key_returns_none(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(decide({"state": "x", "questions": {}}))

    @unittest.skipUnless(
        os.environ.get("JEV_API_KEY", "").strip() or os.environ.get("TYPESAFE_API_KEY", "").strip(),
        "JEV_API_KEY and TYPESAFE_API_KEY are unset",
    )
    def test_live_fixture_has_answers_map(self) -> None:
        body = json.loads((_ROOT / "fixtures" / "decide.json").read_text(encoding="utf-8"))
        result = decide(body)
        self.assertIsInstance(result, dict)
        self.assertIn("answers", result)
        self.assertIsInstance(result["answers"], dict)

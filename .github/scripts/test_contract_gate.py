"""Tests of contract_gate.py: `python -m unittest discover -s .github/scripts -v`."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import contract_gate as gate

KIT_LINE_1_3_0 = (
    '"""docs"""\n'
    "# The tag guard of tribunedesk-cms-api reads this line with a regex.\n"
    "SUPPORTED_MINORS = frozenset({(3, 4)})\n"
    "_VERSION = 1\n"
)

GUIDE = """# 1. Article delivery

Text.

## Done when

- First point.
- Second point.

In read mode, also:

- Third point.

## Next

- Not a point.
"""


def changelog(version: str, items: str = "- Nothing to do.") -> str:
    return (
        "# Changelog\n\nIntro.\n\n"
        f"## {version} – 2026-11-16\n\n- A change.\n\n**Integrators:**\n\n{items}\n\n"
        "## 3.4.2-draft – 2026-11-12\n\n- Old.\n\n**Integrators:**\n\n- Nothing to do.\n"
    )


def write_contract(root: Path, version: str, guide: str = GUIDE, log: str | None = None) -> None:
    (root / "guide").mkdir(parents=True, exist_ok=True)
    (root / "guide" / "1-a.md").write_text(guide, encoding="utf-8")
    (root / "openapi.json").write_text(
        json.dumps({"openapi": "3.1.0", "info": {"version": version}}), encoding="utf-8"
    )
    (root / "CHANGELOG.md").write_text(
        log if log is not None else changelog(version), encoding="utf-8"
    )
    (root / "README.md").write_text("readme\n", encoding="utf-8")


class Rules(unittest.TestCase):
    def test_version_key_orders_draft_before_release(self) -> None:
        self.assertLess(gate.version_key("3.5.0-draft"), gate.version_key("v3.5.0"))
        self.assertGreater(gate.version_key("3.4.10-draft"), gate.version_key("3.4.9-draft"))
        with self.assertRaises(ValueError):
            gate.version_key("latest")

    def test_latest_tag_ignores_foreign_names(self) -> None:
        tags = ["v3.4.1-draft", "v3.4.2-draft", "latest", "v3.4.2"]
        self.assertEqual(gate.latest_tag(tags), "v3.4.2")
        self.assertIsNone(gate.latest_tag(["latest"]))

    def test_done_when_points_include_read_mode_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            write_contract(Path(tmp), "3.4.2-draft")
            self.assertEqual(
                gate.done_when_points(Path(tmp)),
                frozenset(
                    {
                        ("guide/1-a.md", "First point."),
                        ("guide/1-a.md", "Second point."),
                        ("guide/1-a.md", "Third point."),
                    }
                ),
            )

    def test_changelog_needs_heading_and_integrators(self) -> None:
        self.assertEqual(gate.changelog_problems(changelog("3.5.0-draft"), "3.5.0-draft"), [])
        missing = gate.changelog_problems(changelog("3.5.0-draft"), "3.5.1-draft")
        self.assertEqual(len(missing), 1)
        self.assertIn("3.5.1-draft", missing[0])
        no_block = "# Changelog\n\n## 3.5.0-draft – 2026-11-16\n\n- A change.\n\n" + (
            "## 3.4.2-draft – 2026-11-12\n\n**Integrators:**\n\n- Nothing to do.\n"
        )
        self.assertEqual(len(gate.changelog_problems(no_block, "3.5.0-draft")), 1)
        empty_block = (
            "## 3.5.0-draft – 2026-11-16\n\n**Integrators:**\n\n"
            "## 3.4.2-draft\n\n**Integrators:**\n\n- Nothing to do.\n"
        )
        self.assertEqual(len(gate.changelog_problems(empty_block, "3.5.0-draft")), 1)
        tagged = changelog("3.5.0-draft", "- `L3`: filter embeds.")
        self.assertEqual(gate.changelog_problems(tagged, "3.5.0-draft"), [])

    def test_parse_supported_minors_reads_the_kit_line(self) -> None:
        self.assertEqual(gate.parse_supported_minors(KIT_LINE_1_3_0), frozenset({(3, 4)}))
        two = "SUPPORTED_MINORS = frozenset({(3, 4), (3, 5)})\n"
        self.assertEqual(gate.parse_supported_minors(two), frozenset({(3, 4), (3, 5)}))

    def test_parse_supported_minors_rejects_other_forms(self) -> None:
        for text in (
            "nothing here\n",
            "SUPPORTED_MINORS = frozenset({\n    (3, 4),\n})\n",
            "SUPPORTED_MINOR = (3, 4)\n",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError) as caught:
                gate.parse_supported_minors(text)
            self.assertIn("cannot read SUPPORTED_MINORS", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

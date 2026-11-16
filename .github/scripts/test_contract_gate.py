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


def no_kit() -> tuple[str, frozenset[tuple[int, int]]]:
    raise AssertionError("tdkit must not be asked when the minor does not change")


class Decide(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name) / "base"
        self.head = Path(self._tmp.name) / "head"
        write_contract(self.base, "3.4.2-draft", log=changelog("3.4.2-draft"))
        write_contract(self.head, "3.4.2-draft", log=changelog("3.4.2-draft"))

    def decide(self, kit: gate.KitMinors = no_kit) -> gate.Decision:
        return gate.decide(self.head, self.base, "v3.4.2-draft", kit)

    def test_decide_no_change_is_no_tag(self) -> None:
        self.assertEqual(self.decide(), gate.Decision(None, []))

    def test_decide_outside_contract_paths_is_no_change(self) -> None:
        (self.head / "README.md").write_text("new readme\n", encoding="utf-8")
        (self.head / "pl" / "guide").mkdir(parents=True)
        (self.head / "pl" / "guide" / "1-a.md").write_text("tekst\n", encoding="utf-8")
        self.assertEqual(self.decide(), gate.Decision(None, []))

    def test_decide_changed_without_version_is_a_problem(self) -> None:
        (self.head / "guide" / "1-a.md").write_text(GUIDE + "\nMore text.\n", encoding="utf-8")
        decision = self.decide()
        self.assertIsNone(decision.tag)
        self.assertTrue(any("changed without a new version" in p for p in decision.problems))

    def test_decide_patch_bump_tags(self) -> None:
        write_contract(self.head, "3.4.3-draft", guide=GUIDE.replace("Text.", "Clearer text."))
        self.assertEqual(self.decide(), gate.Decision("v3.4.3-draft", []))

    def test_decide_new_done_when_point_needs_minor(self) -> None:
        guide = GUIDE.replace("- Second point.", "- Second point.\n- New point.")
        write_contract(self.head, "3.4.3-draft", guide=guide)
        decision = self.decide()
        self.assertIsNone(decision.tag)
        self.assertTrue(any("bump at least the minor" in p for p in decision.problems))

    def test_decide_new_minor_unknown_to_kit_is_refused(self) -> None:
        write_contract(self.head, "3.5.0-draft")
        decision = self.decide(lambda: ("v1.3.0", frozenset({(3, 4)})))
        self.assertIsNone(decision.tag)
        self.assertTrue(
            any("release tdkit that knows 3.5 first" in p for p in decision.problems),
            decision.problems,
        )

    def test_decide_new_minor_known_to_kit_tags(self) -> None:
        guide = GUIDE.replace("- Second point.", "- Second point.\n- New point.")
        write_contract(self.head, "3.5.0-draft", guide=guide)
        decision = self.decide(lambda: ("v1.4.0", frozenset({(3, 4), (3, 5)})))
        self.assertEqual(decision, gate.Decision("v3.5.0-draft", []))

    def test_decide_older_version_is_a_problem(self) -> None:
        write_contract(self.head, "3.4.1-draft", log=changelog("3.4.1-draft"))
        decision = self.decide()
        self.assertIsNone(decision.tag)
        self.assertTrue(any("not newer than v3.4.2-draft" in p for p in decision.problems))

    def test_decide_bad_changelog_is_a_problem(self) -> None:
        write_contract(self.head, "3.4.3-draft", log=changelog("3.4.2-draft"))
        decision = self.decide()
        self.assertIsNone(decision.tag)
        self.assertTrue(any("## 3.4.3-draft" in p for p in decision.problems))


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


class Main(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name) / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.name", "t")
        git(self.repo, "config", "user.email", "t@example.invalid")
        git(self.repo, "config", "core.autocrlf", "false")
        write_contract(self.repo, "3.4.2-draft", log=changelog("3.4.2-draft"))
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "3.4.2")
        self.output = Path(self._tmp.name) / "output"
        self.output.write_text("", encoding="utf-8")
        self._env = os.environ.get("GITHUB_OUTPUT")
        os.environ["GITHUB_OUTPUT"] = str(self.output)
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        if self._env is None:
            os.environ.pop("GITHUB_OUTPUT", None)
        else:
            os.environ["GITHUB_OUTPUT"] = self._env

    def test_main_on_repo_writes_tag_output(self) -> None:
        git(self.repo, "tag", "v3.4.2-draft")
        write_contract(self.repo, "3.4.3-draft")
        git(self.repo, "commit", "-q", "-am", "3.4.3")
        self.assertEqual(gate.main(["--repo", str(self.repo)]), 0)
        self.assertIn("tag=v3.4.3-draft\n", self.output.read_text(encoding="utf-8"))

    def test_main_no_change_writes_empty_tag(self) -> None:
        git(self.repo, "tag", "-a", "v3.4.2-draft", "-m", "Contract v3.4.2-draft")
        self.assertEqual(gate.main(["--repo", str(self.repo)]), 0)
        self.assertIn("tag=\n", self.output.read_text(encoding="utf-8"))

    def test_main_without_tags_fails(self) -> None:
        self.assertEqual(gate.main(["--repo", str(self.repo)]), 1)

    def test_main_bad_openapi_fails(self) -> None:
        git(self.repo, "tag", "v3.4.2-draft")
        (self.repo / "openapi.json").write_text("{", encoding="utf-8")
        self.assertEqual(gate.main(["--repo", str(self.repo)]), 1)


if __name__ == "__main__":
    unittest.main()

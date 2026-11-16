"""Gate of the contract tag: may this tree become a new tag, and which one?

    python3 .github/scripts/contract_gate.py [--repo DIR]

Run by `.github/workflows/pr.yml` (on pull requests to `main`) and `tag.yml` (on push to `main`,
which then sets the tag). Spec: `docs/specs/2026-11-13-kontrakt-najpierw-automaty-design.md` in
Tribunedesk/tribunedesk-cms-kit, D2a and D2c.

It compares the contract files of the checkout with the newest `v*` tag. Nothing changed: no tag.
Changed: `info.version` of `openapi.json` must be newer than the tag, the CHANGELOG must have its
heading with an `**Integrators:**` list, a changed set of "Done when" points needs at least a
new minor, and a new minor or major needs a tdkit release that knows it (`SUPPORTED_MINORS` in
`src/tdkit/docs.py` of the newest tdkit tag). Problems go to stderr as `::error::` and exit 1;
otherwise `tag=<v...>` (or `tag=`) goes to `$GITHUB_OUTPUT`.

This file lives under `.github/` on purpose: the docs sync of headlinesforge deletes every other
file it does not publish. Network: `git ls-remote` and a shallow `git clone` of the public tdkit
repository, only when the minor changes.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

CONTRACT_PATHS = ("openapi.json", "CHANGELOG.md", "guide", "examples")
KIT_URL = "https://github.com/Tribunedesk/tribunedesk-cms-kit"
KIT_DOCS = "src/tdkit/docs.py"
_KIT_TAG = re.compile(r"refs/tags/(v(\d+)\.(\d+)\.(\d+))$")

_VERSION = re.compile(r"v?(\d+)\.(\d+)\.(\d+)(-draft)?")
_MINORS_LINE = re.compile(r"^SUPPORTED_MINORS = frozenset\(\{((?:\(\d+, \d+\)(?:, )?)+)\}\)$", re.M)


def version_key(version: str) -> tuple[int, int, int, int]:
    """Order of contract versions: a draft comes before the release of the same numbers."""
    match = _VERSION.fullmatch(version.strip())
    if not match:
        raise ValueError(f"not a contract version: {version!r}")
    return int(match[1]), int(match[2]), int(match[3]), 0 if match[4] else 1


def latest_tag(tags: list[str]) -> str | None:
    """The newest `v*` contract tag; other names are ignored."""
    versions = [t for t in tags if t.startswith("v") and _VERSION.fullmatch(t)]
    return max(versions, key=version_key, default=None)


def contract_files(root: Path) -> dict[str, bytes]:
    """Posix path -> bytes of every file under `CONTRACT_PATHS`."""
    files: dict[str, bytes] = {}
    for name in CONTRACT_PATHS:
        path = root / name
        if path.is_file():
            files[name] = path.read_bytes()
        elif path.is_dir():
            for item in sorted(path.rglob("*")):
                if item.is_file():
                    files[item.relative_to(root).as_posix()] = item.read_bytes()
    return files


def done_when_points(root: Path) -> frozenset[tuple[str, str]]:
    """`(guide/<file>, point)` for every bullet of every "## Done when" section.

    The same rule as `done_when_points` in tdkit's `tests/test_coverage.py`.
    """
    points: set[tuple[str, str]] = set()
    for path in sorted((root / "guide").glob("*.md")):
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        if "\n## Done when\n" not in text:
            continue
        section = text.split("\n## Done when\n", 1)[1].split("\n## ", 1)[0]
        for line in section.splitlines():
            if line.startswith("- "):
                points.add((f"guide/{path.name}", line[2:].strip()))
    return frozenset(points)


def changelog_problems(changelog: str, version: str) -> list[str]:
    """The CHANGELOG has `## <version>` with an `**Integrators:**` list of at least one item."""
    lines = changelog.replace("\r\n", "\n").splitlines()
    heading = re.compile(rf"^## {re.escape(version)}(\s|$)")
    start = next((i for i, line in enumerate(lines) if heading.match(line)), None)
    if start is None:
        return [f"CHANGELOG.md has no heading `## {version}`"]
    section: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        section.append(line)
    if "**Integrators:**" not in (line.strip() for line in section):
        return [f'CHANGELOG.md {version} has no `**Integrators:**` list ("Nothing to do." counts)']
    after = section[[line.strip() for line in section].index("**Integrators:**") + 1 :]
    # The list is the bullets right under the line; blank lines before it are allowed, and any
    # other line (a paragraph, a `### ` heading) ends it.
    first = next((line for line in after if line.strip()), "")
    if not first.startswith("- "):
        return [f"CHANGELOG.md {version}: the `**Integrators:**` list is empty"]
    return []


def parse_supported_minors(docs_py: str) -> frozenset[tuple[int, int]]:
    """`SUPPORTED_MINORS` of tdkit's `src/tdkit/docs.py`; anything else is an error."""
    match = _MINORS_LINE.search(docs_py.replace("\r\n", "\n"))
    if not match:
        raise ValueError(
            "cannot read SUPPORTED_MINORS from tdkit's src/tdkit/docs.py: expected one line "
            "`SUPPORTED_MINORS = frozenset({(3, 4), ...})`"
        )
    pairs = re.findall(r"\((\d+), (\d+)\)", match[1])
    return frozenset((int(a), int(b)) for a, b in pairs)


@dataclass(frozen=True)
class Decision:
    """`tag` is set only when the contract changed and nothing is wrong."""

    tag: str | None
    problems: list[str]


KitMinors = Callable[[], tuple[str, frozenset[tuple[int, int]]]]


def read_version(root: Path) -> str:
    """`info.version` of `root/openapi.json`; `ValueError` when it cannot be read."""
    try:
        version = json.loads((root / "openapi.json").read_text(encoding="utf-8"))["info"]["version"]
        if not re.fullmatch(r"\d+\.\d+\.\d+(-draft)?", version):
            raise ValueError(f"{version!r} is not X.Y.Z or X.Y.Z-draft")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"openapi.json: cannot read info.version ({exc})") from exc
    return version


def decide(head: Path, base: Path, base_tag: str, kit: KitMinors) -> Decision:
    """May the contract files of `head` become a new tag after `base` (the tree of `base_tag`)?

    `kit` returns the newest tdkit tag and its `SUPPORTED_MINORS`; it is called only when the
    major or minor changes.
    """
    if contract_files(head) == contract_files(base):
        return Decision(None, [])
    try:
        version = read_version(head)
    except ValueError as exc:
        return Decision(None, [str(exc)])
    new, old = version_key(version), version_key(base_tag)
    if new <= old:
        return Decision(
            None,
            [
                f"contract files changed without a new version: info.version {version} "
                f"is not newer than {base_tag}"
            ],
        )
    problems = changelog_problems((head / "CHANGELOG.md").read_text(encoding="utf-8"), version)
    if new[:2] == old[:2] and done_when_points(head) != done_when_points(base):
        problems.append(
            f'the "Done when" points differ from {base_tag}: a new requirement, '
            f"bump at least the minor (info.version is {version})"
        )
    if new[:2] != old[:2]:
        wanted = f"{new[0]}.{new[1]}"
        try:
            kit_tag, minors = kit()
        except (ValueError, OSError, subprocess.CalledProcessError) as exc:
            problems.append(f"cannot check that tdkit knows {wanted}: {exc}")
        else:
            if new[:2] not in minors:
                known = ", ".join(f"{a}.{b}" for a, b in sorted(minors))
                problems.append(
                    f"release tdkit that knows {wanted} first "
                    f"(tdkit {kit_tag} supports {known}; SUPPORTED_MINORS in {KIT_DOCS})"
                )
    return Decision(None if problems else f"v{version}", problems)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout


def export_tag(repo: Path, tag: str, dest: Path) -> None:
    """Write the contract files of `tag` to `dest`."""
    present = set(_git(repo, "ls-tree", "--name-only", tag).split())
    paths = [p for p in CONTRACT_PATHS if p in present]
    if not paths:
        return
    archive = subprocess.run(
        ["git", "-C", str(repo), "archive", "--format=tar", tag, "--", *paths],
        check=True,
        capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(dest, filter="data")


def kit_minors() -> tuple[str, frozenset[tuple[int, int]]]:
    """The newest tdkit tag and the `SUPPORTED_MINORS` of its `src/tdkit/docs.py`."""
    refs = subprocess.run(
        ["git", "ls-remote", "--tags", "--refs", KIT_URL],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout
    tags = [m for m in (_KIT_TAG.search(line.strip()) for line in refs.splitlines()) if m]
    if not tags:
        raise ValueError(f"no vX.Y.Z tag in {KIT_URL}")
    newest = max(tags, key=lambda m: (int(m[2]), int(m[3]), int(m[4])))[1]
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["git", "clone", "--quiet", "--depth", "1", "--branch", newest, KIT_URL, tmp],
            check=True,
            capture_output=True,
        )
        text = (Path(tmp) / KIT_DOCS).read_text(encoding="utf-8")
    return newest, parse_supported_minors(text)


def _output(tag: str | None) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with Path(path).open("a", encoding="utf-8") as out:
            out.write(f"tag={tag or ''}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gate of the contract tag (spec D2a, D2c).")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="checkout to check")
    args = parser.parse_args(argv)
    repo: Path = args.repo.resolve()
    base_tag = latest_tag(_git(repo, "tag", "--list", "v*").split())
    if base_tag is None:
        print("::error::no v* tag in this repository", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        export_tag(repo, base_tag, Path(tmp))
        decision = decide(repo, Path(tmp), base_tag, kit_minors)
    for problem in decision.problems:
        print(f"::error::{problem}", file=sys.stderr)
    if decision.problems:
        return 1
    if decision.tag:
        print(f"Contract changed since {base_tag}: tag {decision.tag}.")
    else:
        print(f"No contract change since {base_tag}: no tag.")
    _output(decision.tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())

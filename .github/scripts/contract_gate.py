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

import re
from pathlib import Path

CONTRACT_PATHS = ("openapi.json", "CHANGELOG.md", "guide", "examples")

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
        return [f"CHANGELOG.md {version} has no `**Integrators:**` list (\"Nothing to do.\" counts)"]
    after = section[[line.strip() for line in section].index("**Integrators:**") + 1 :]
    if not any(line.startswith("- ") for line in after):
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

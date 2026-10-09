#!/usr/bin/env python3
"""Classify every dependency in requirements/snapshots and print a Markdown report.

    python scripts/pin_report.py                 # report
    python scripts/pin_report.py --fail-on-unpinned   # exit 1 if any dependency has no version at all

Kinds: pinned (==x.y.z), bounded (has an upper bound or ==x.*), lower-only (>= with no upper bound),
unpinned (no version), editable (-e path). Lower-only and unpinned are what let a fresh image build pull a newer
release than the one that was tested.
"""
import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent / "requirements" / "snapshots"
LINE = re.compile(r"^([A-Za-z0-9_.\-]+)(\[[^\]]+\])?\s*(.*)$")


def kind_of(spec: str) -> str:
    if not spec:
        return "unpinned"
    if "==" in spec and "*" not in spec:
        return "pinned"
    if "<" in spec or "*" in spec or "~=" in spec:
        return "bounded"
    return "lower-only"


def load():
    rows = []
    for f in sorted(ROOT.rglob("*requirements*.txt")) + sorted(ROOT.rglob("inline-pins.txt")):
        svc = f.relative_to(ROOT).parts[0]
        for raw in f.read_text().splitlines():
            s = raw.split("#")[0].split(";")[0].strip()
            if not s or s.startswith(("-r", "--")):
                continue
            if s.startswith("-e"):
                rows.append((svc, "(editable) " + s[2:].strip(), "", "editable"))
                continue
            m = LINE.match(s)
            if m:
                name = m.group(1).lower().replace("_", "-")
                spec = m.group(3).strip()
                rows.append((svc, name, spec, kind_of(spec)))
    return rows


def main():
    rows = load()
    kinds = ["pinned", "bounded", "lower-only", "unpinned"]
    count = collections.Counter((r[0], r[3]) for r in rows)
    print("## Pin status per service\n")
    print("| Service | pinned | bounded | lower-only | unpinned |\n|---|---:|---:|---:|---:|")
    for s in sorted({r[0] for r in rows}):
        print(f"| {s} | " + " | ".join(str(count[(s, k)]) for k in kinds) + " |")
    tot = collections.Counter(r[3] for r in rows)
    print("| **total** | " + " | ".join(f"**{tot[k]}**" for k in kinds) + " |\n")

    print("## Unpinned (no version at all)\n")
    by = collections.defaultdict(list)
    for s, n, sp, k in rows:
        if k == "unpinned":
            by[s].append(n)
    for s in sorted(by):
        print(f"- **{s}**: " + ", ".join(sorted(set(by[s]))))

    print("\n## Specified differently across services\n")
    pk = collections.defaultdict(list)
    for s, n, sp, k in rows:
        if k != "editable":
            pk[n].append((s, sp or "(none)"))
    print("| Package | Specs by service |\n|---|---|")
    for n, v in sorted(pk.items()):
        if len({sp for _, sp in v}) > 1 and len({s for s, _ in v}) > 1:
            print(f"| `{n}` | " + "; ".join(f"{s}: `{sp}`" for s, sp in v) + " |")

    bad = tot["unpinned"]
    return 1 if ("--fail-on-unpinned" in sys.argv and bad) else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Deterministic Impl:-line trace checker (ADR-005/ADR-005a). Stdlib only.

A marker is the substring from 'Impl:' to end-of-line, anywhere on a
docs/*.md line, excluding quoted/backticked prose mentions. Each marker
must be EXACTLY 'Impl: TBD' or 'Impl: [<path>:L<a>-L<b>](<relpath>)'.
"""
import glob
import os
import re
import sys

FILLED = re.compile(r"^Impl: \[([^\]:]+):L(\d+)-L(\d+)\]\(([^)]+)\)$")
QUOTES = ("`", "'", '"')


def find_marker(line):
    """Return index of a marker tail: exact 'Impl: TBD' at EOL, or a
    filled 'Impl: [' form. Quoted mentions and prose are not markers."""
    idx = 0
    while (i := line.find("Impl:", idx)) != -1:
        idx = i + 1
        if i > 0 and line[i - 1] in QUOTES:
            continue
        tail = line[i:]
        if tail == "Impl: TBD" or tail.startswith("Impl: ["):
            return i
    return None


def main():
    total = filled = tbd = 0
    errors = []
    for doc in sorted(p.replace(os.sep, "/") for p in glob.glob("docs/*.md")):
        with open(doc, encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, 1):
                line = raw.rstrip("\n")
                i = find_marker(line)
                if i is None:
                    continue
                total += 1
                tail = line[i:]
                if tail == "Impl: TBD":
                    tbd += 1
                    continue
                m = FILLED.match(tail)
                if not m:
                    errors.append(f"TRACE_ERR {doc}:{lineno} malformed Impl line")
                    continue
                a, b, rel = int(m.group(2)), int(m.group(3)), m.group(4)
                if not os.path.exists(rel):
                    errors.append(f"TRACE_ERR {doc}:{lineno} missing target {rel}")
                    continue
                with open(rel, encoding="utf-8") as target:
                    nlines = sum(1 for _ in target)
                if a > b:
                    errors.append(f"TRACE_ERR {doc}:{lineno} range L{a}>L{b}")
                elif b > nlines:
                    errors.append(f"TRACE_ERR {doc}:{lineno} L{b} beyond {rel} ({nlines} lines)")
                else:
                    filled += 1
    print(f"TRACE total={total} filled={filled} tbd={tbd}")
    if tbd:
        print(f"PARTIAL: {tbd} sections unimplemented")
    if errors:
        print("\n".join(errors))
        return 1
    print("TRACE_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

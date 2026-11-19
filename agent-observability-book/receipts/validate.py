"""Validates Agent Receipt v0.1 records and their hash chain.

Usage: python -m receipts.validate RECORD.json [RECORD.json ...]

Used in Chapter 2. Pass chained records in order. Each one is checked
against its schema, its own hash is recomputed, and its prev_hash must
match the hash of the chained record before it. R1-R3 receipts without
an integrity block are checked against the schema only and reported as
unchained.
"""
import json
import pathlib
import sys
import textwrap

from jsonschema import Draft202012Validator, FormatChecker

from receipts.tools import GENESIS, record_hash

HERE = pathlib.Path(__file__).parent


def _validator(name):
    schema = json.loads((HERE / name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


RECEIPT = _validator("agent-receipt.schema.json")
OUTCOME = _validator("agent-outcome.schema.json")

QUESTIONS = [
    ("who", "who acted"), ("for_whom", "for whom"),
    ("knowing_what", "knowing what"),
    ("under_which_rule", "under which rule"),
    ("did_what", "doing what"), ("at_what_cost", "at what cost"),
    ("where", "where"),
]


def unanswered(rec):
    """Labels of the seven questions this receipt cannot answer."""
    return [label for key, label in QUESTIONS if key not in rec]


def check(paths):
    ok, prev = True, None
    for path in paths:
        path = pathlib.Path(path)
        rec = json.loads(path.read_text(encoding="utf-8"))
        is_outcome = rec.get("record_type") == "outcome"
        schema = OUTCOME if is_outcome else RECEIPT
        errors = sorted(schema.iter_errors(rec), key=lambda e: list(e.path))
        if errors:
            ok = False
            for e in errors:
                where = "/".join(map(str, e.path)) or "(root)"
                print(f"FAIL {path.name}: {where}: {e.message}")
            continue

        integrity = rec.get("integrity")
        if integrity is None:
            chain = "unchained"
        elif record_hash(rec) != integrity["hash"]:
            ok = False
            print(f"FAIL {path.name}: hash does not match; record altered")
            continue
        elif integrity["prev_hash"] != (prev or GENESIS):
            ok = False
            print(f"FAIL {path.name}: prev_hash breaks the chain")
            continue
        else:
            prev, chain = integrity["hash"], "chained"

        if is_outcome:
            print(f"PASS {path.name}: outcome {rec['status']}, {chain}")
            print(f"     resolves {rec['receipt_id']}")
            continue
        missing = unanswered(rec)
        print(f"PASS {path.name}: {rec['conformance']}, "
              f"answers {7 - len(missing)}/7, {chain}")
        if missing:
            print(textwrap.fill("cannot answer: " + ", ".join(missing),
                                width=64, initial_indent="     ",
                                subsequent_indent="     "))
    return ok


if __name__ == "__main__":
    sys.exit(0 if check(sys.argv[1:]) else 1)

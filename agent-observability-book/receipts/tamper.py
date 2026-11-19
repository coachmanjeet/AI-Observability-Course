"""The tamper test: change one amount and watch the chain catch it.

Usage: python -m receipts.tamper

Used in Chapter 2. Copies Speedy's $40 refund, changes the amount to
$400 without touching its hash, and validates it after the order
lookup it is chained to. Expect a FAIL and exit code 1.
"""
import json
import pathlib
import sys
import tempfile

from receipts.validate import check

EXAMPLES = pathlib.Path(__file__).parent / "examples"

if __name__ == "__main__":
    refund = json.loads((EXAMPLES / "02-speedy-refund-40.json").read_text())
    refund["did_what"]["effect"]["amount"]["value"] = "400.00"
    with tempfile.TemporaryDirectory() as tmp:
        altered = pathlib.Path(tmp) / "02-tampered.json"
        altered.write_text(json.dumps(refund, indent=2))
        ok = check([EXAMPLES / "01-speedy-order-lookup.json", altered])
    sys.exit(0 if ok else 1)

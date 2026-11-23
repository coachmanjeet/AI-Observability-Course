"""RFC 8785, section 3.2.3: sorting of object properties."""
import json

from receipts.tools import canonical

VECTOR = {"€": "Euro Sign", "\r": "Carriage Return",
          "דּ": "Hebrew Letter Dalet With Dagesh",
          "1": "One", "\U0001f600": "Emoji: Grinning Face",
          "\u0080": "Control",
          "ö": "Latin Small Letter O With Diaeresis"}
EXPECTED = ["\r", "1", "\u0080", "ö", "€",
            "\U0001f600", "דּ"]


def test_rfc8785_property_order():
    keys = list(json.loads(canonical(VECTOR)))
    assert keys == EXPECTED


def test_python_sort_keys_would_get_it_wrong():
    keys = list(json.loads(json.dumps(VECTOR, sort_keys=True)))
    assert keys != EXPECTED

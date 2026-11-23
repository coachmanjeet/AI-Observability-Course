"""Chapter 6: capture, redaction, tail sampling and cost."""
import json
import pathlib

import pytest
import yaml

from collector import processors as p
from collector.night import canaries, night
from collector.prices import model_cost
from decisions.run import turns
from receipts.from_trace import load_inventory, receipts
from telemetry import otlp
from telemetry.lint import lint

ROOT = pathlib.Path(__file__).parent.parent
EXAMPLE = json.loads((ROOT / "receipts" / "examples" /
                      "02-speedy-refund-40.json").read_text())
INVENTORY = load_inventory(ROOT / "maturity" / "fleet.json")


@pytest.fixture(scope="module")
def stages(tmp_path_factory):
    out = tmp_path_factory.mktemp("night") / "received.json"
    spans, plan = night(300)
    otlp.write(spans, out)
    received = otlp.load(out)
    redacted = p.redact(received)
    kept, reasons = p.tail_sample(redacted)
    return received, redacted, kept, reasons, canaries(plan)


def test_content_capture_put_customers_in_the_trace(stages):
    received, _, _, _, found = stages
    assert p.leaks(received, found) > 0
    _, findings = lint(received)
    assert any("captures content" in m for _, _, m in findings)


def test_redaction_removes_every_canary(stages):
    _, redacted, kept, _, found = stages
    assert p.leaks(redacted, found) == p.leaks(kept, found) == 0
    _, findings = lint(redacted)
    assert findings == []                    # still a valid trace


def test_an_email_in_the_wrong_field_is_masked(stages):
    _, redacted, _, _, _ = stages
    masked = [s for s in redacted
              if "redaction.masked.count" in s["attributes"]]
    assert masked and all(s["attributes"]["pronto.tool.target"]
                          == "order:****" for s in masked)


def test_tail_sampling_keeps_every_incident(stages):
    _, redacted, kept, reasons, _ = stages
    trouble = p.incidents(redacted)
    assert trouble and trouble <= set(p.traces(kept))
    head = set(p.traces(p.head_sample(redacted)))
    assert len(trouble & head) < len(trouble) / 2
    assert reasons["action"] > 0 and reasons["baseline"] > 0


def test_tail_sampling_keeps_whole_traces(stages):
    _, redacted, kept, _, _ = stages
    every = p.traces(redacted)
    for tid, members in p.traces(kept).items():
        assert len(members) == len(every[tid])


def test_receipts_come_from_unsampled_spans(stages):
    _, redacted, kept, _, _ = stages
    before = list(receipts(redacted, INVENTORY, with_cost=True))
    after = list(receipts(kept, INVENTORY, with_cost=True))
    assert len(after) < len(before)
    assert all("at_what_cost" in r for r in before)


def test_model_cost_is_exact():
    assert model_cost("pronto-mock-1", 3120, 410, 1800) == "0.0142"
    assert model_cost("pronto-mock-1", 2410, 96, 1800) == "0.00508"


def test_refund_cost_matches_chapter_2(tmp_path):
    otlp.write(turns()[0], tmp_path / "d.json")
    spans = otlp.load(tmp_path / "d.json")
    refund = next(r for r in receipts(spans, INVENTORY, with_cost=True)
                  if r["evidence"]["span_id"] == "00f067aa0ba902b7")
    want = EXAMPLE["at_what_cost"]
    assert refund["at_what_cost"]["tokens"] == want["tokens"]
    assert refund["at_what_cost"]["model_cost"] == want["model_cost"]


def test_collector_config_matches_the_lab():
    config = yaml.safe_load((ROOT / "collector" /
                             "pronto-collector.yaml").read_text())
    redaction = config["processors"]["redaction"]
    assert set(redaction["allowed_keys"]) == p.ALLOWED_KEYS
    assert redaction["blocked_values"] == [
        r.pattern for r in p.BLOCKED_VALUES]
    names = [x["name"] for x in
             config["processors"]["tail_sampling"]["policies"]]
    assert names == ["errors", "actions", "slow", "baseline"]
    pipes = config["service"]["pipelines"]
    assert "tail_sampling" not in pipes["traces/receipts"]["processors"]


def test_stored_traces_overstate_incidents_and_understate_cost(
        stages):
    from collector.run import night_cost
    _, redacted, kept, _, _ = stages
    trouble = p.incidents(redacted)
    all_rate = len(trouble) / len(p.traces(redacted))
    stored_rate = len(trouble) / len(p.traces(kept))
    assert stored_rate > 2 * all_rate
    assert night_cost(kept) < night_cost(redacted)

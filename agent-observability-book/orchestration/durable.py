"""A durable, multi-modal workflow for Route (Chapter 17).

Usage: python -m orchestration.durable [OUT_DIR]

A small stand-in for a durable workflow engine such as Temporal.
The workflow's history is an append-only list of events. On
every run the workflow code replays from the top; steps already
in the history return their recorded results instead of running
again. Side effects carry idempotency keys, so a crash between a
side effect and its checkpoint can't repeat it. Each step gets
its own trace, linked to the workflow, and each consequential
step gets a receipt linked to the one before it.
"""
import hashlib
import json
import pathlib
import sys

WF = "wf_7c21"


def ids(step):
    h = hashlib.sha256(f"{WF}:{step}".encode()).hexdigest()
    return h[:32], h[32:48]


class Crash(Exception):
    """The worker died; the history survives."""


class Payments:
    """Credits with idempotency keys, as Pronto's API has."""

    def __init__(self):
        self.credits, self.attempts = {}, 0

    def credit(self, key, amount):
        self.attempts += 1
        if key not in self.credits:
            n = len(self.credits) + 1
            self.credits[key] = {"id": f"cr_{n}",
                                 "amount": amount}
        return self.credits[key]["id"]


class Bridge:
    """The phone bridge. v2 forwards traceparent in call
    metadata; v1, the one Chapter 4 found, dropped it."""

    def __init__(self, version=2):
        self.version, self.calls = version, []

    def call(self, who, ask, traceparent):
        kept = traceparent if self.version >= 2 else None
        self.calls.append({"to": who, "traceparent": kept})
        answers = {"customer": "redeliver 8-10 am",
                   "driver d_118": "accepts"}
        return answers[who]


class Run:
    """One execution of the workflow against its history."""

    def __init__(self, history, world, crash_at=None):
        self.h, self.w, self.crash_at = history, world, crash_at
        self.i, self.replayed, self.effects = 0, 0, 0

    def step(self, name, at, fn):
        if self.i < len(self.h):
            ev = self.h[self.i]
            assert ev["step"] == name, "non-deterministic code"
            self.i += 1
            self.replayed += 1
            return ev["result"]
        result = fn()
        self.effects += 1
        if self.crash_at == name:
            raise Crash(name)
        trace_id, span_id = ids(name)
        self.h.append({"seq": len(self.h) + 1, "step": name,
                       "at": at, "result": result,
                       "trace_id": trace_id,
                       "span_id": span_id})
        self.i += 1
        return result


def route_workflow(run):
    """Damaged box: inspect, call, wait, dispatch, credit."""
    w = run.w
    damage = run.step("vision", "Mon 14:02",
                      lambda: "box crushed")
    tp = "00-{}-{}-01".format(*ids("voice-customer"))
    slot = run.step("voice-customer", "Mon 14:05",
                    lambda: w["bridge"].call("customer",
                                             "redeliver?", tp))
    run.step("timer", "Mon 14:06", lambda: "until Tue 08:00")
    tp = "00-{}-{}-01".format(*ids("voice-driver"))
    run.step("voice-driver", "Tue 08:00",
             lambda: w["bridge"].call("driver d_118",
                                      f"redeliver {slot}", tp))
    run.step("credit", "Tue 08:41",
             lambda: w["payments"].credit(f"{WF}:fee", "5.99"))
    return damage


def execute(world, crashes):
    """Run until done, restarting after each crash."""
    history, log = [], []
    for crash_at in crashes + [None]:
        run = Run(history, world, crash_at)
        try:
            route_workflow(run)
            log.append(("done", run.replayed, run.effects))
            return history, log
        except Crash as c:
            log.append((f"crash in {c}", run.replayed,
                        run.effects))
    return history, log


RECEIPTED = {"voice-customer": "external_communication",
             "voice-driver": "external_communication",
             "credit": "financial"}


def receipts(history):
    """Evidence for each consequential step, chained."""
    out, prev = [], None
    for ev in history:
        if ev["step"] not in RECEIPTED:
            continue
        rid = f"rcpt_{WF}_{ev['seq']}"
        evidence = {"trace_id": ev["trace_id"],
                    "span_id": ev["span_id"],
                    "conversation_id": WF}
        if prev:
            evidence["parent_receipt_id"] = prev
        out.append({"receipt_id": rid,
                    "consequence": {"side_effect":
                                    RECEIPTED[ev["step"]]},
                    "evidence": evidence})
        prev = rid
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    world = {"bridge": Bridge(2), "payments": Payments()}
    history, log = execute(world, ["timer", "credit"])
    print(f"Route: delivery exception {WF}, "
          "Mon 14:02 to Tue 08:41")
    for ev in history:
        print(f"  {ev['at']:<10} {ev['step']:<15}"
              f"{ev['result']:<22}#{ev['seq']}")
    for what, replayed, effects in log:
        print(f"  run: {what:<20} replayed {replayed}, "
              f"ran {effects}")
    pay = world["payments"]
    print(f"credits issued: {len(pay.credits)} "
          f"({pay.attempts} attempts)")
    kept = sum(c["traceparent"] is not None
               for c in world["bridge"].calls)
    v1 = Bridge(1)
    v1.call("customer", "redeliver?", "00-x-y-01")
    lost = sum(c["traceparent"] is None for c in v1.calls)
    print(f"phone bridge v2 kept traceparent: {kept} of "
          f"{len(world['bridge'].calls)} (v1 lost {lost} of 1)")
    rec = receipts(history)
    print(f"receipts: {len(rec)}, chained by parent_receipt_id")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        (out / "history.json").write_text(
            json.dumps(history, indent=2) + "\n")
        (out / "credit-evidence.json").write_text(json.dumps(
            {"evidence": rec[-1]["evidence"]}, indent=2) + "\n")


if __name__ == "__main__":
    main()

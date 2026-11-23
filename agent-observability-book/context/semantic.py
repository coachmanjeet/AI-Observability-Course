"""Governed metrics over Pronto's tables (Chapter 8).

Usage: python -m context.semantic [OUT_DIR]

Pick asks which substitutions fell below 50% acceptance last week.
One answer comes from SQL written against the raw tables, the way a
text-to-SQL model writes it. The other comes from the governed
metric in context/metrics.yaml, compiled by this module. They
disagree, and only one of them may change what Pick does.
"""
import json
import pathlib
import sys

import duckdb
import yaml

from receipts.tools import digest

HERE = pathlib.Path(__file__).parent
METRICS = yaml.safe_load((HERE / "metrics.yaml").read_text())
WEEK = ("2026-12-07", "2026-12-14")
THRESHOLD = 0.5

# What a model wrote from the schema alone: it joins order lines
# (one row per item, so big baskets count more) and keeps test
# and cancelled orders.
RAW_SQL = """
select s.original || ' -> ' || s.substitute as pair,
       avg(case when s.accepted then 1.0 else 0 end) as rate
from substitutions s
join order_lines l on l.order_id = s.order_id
join orders o on o.order_id = s.order_id
where o.placed_at >= ? and o.placed_at < ?
group by pair order by pair
"""

# (original, substitute, accepted, rejected, lines if accepted,
#  lines if rejected, test-order rejections)
PAIRS = [("oat milk", "almond milk", 30, 10, 2, 2, 50),
         ("peanut butter", "almond butter", 6, 14, 5, 1, 0),
         ("strawberries", "raspberries", 10, 15, 3, 3, 0),
         ("whole milk", "2% milk", 45, 5, 2, 2, 0)]


def load():
    """An in-memory warehouse holding last week's orders."""
    db = duckdb.connect()
    db.execute("create table orders (order_id int, placed_at"
               " date, status text)")
    db.execute("create table order_lines (order_id int, sku int)")
    db.execute("create table substitutions (order_id int, original"
               " text, substitute text, accepted boolean)")
    oid = 1000
    for orig, sub, yes, no, big, small, tests in PAIRS:
        rows = [(True, big, "delivered")] * yes \
            + [(False, small, "delivered")] * no \
            + [(False, 1, "test")] * tests
        for i, (ok, lines, status) in enumerate(rows):
            oid += 1
            day = f"2026-12-{7 + i % 7:02d}"
            db.execute("insert into orders values (?, ?, ?)",
                       [oid, day, status])
            for sku in range(lines):
                db.execute("insert into order_lines values (?, ?)",
                           [oid, sku])
            db.execute("insert into substitutions values"
                       " (?, ?, ?, ?)", [oid, orig, sub, ok])
    return db


def compile_metric(name, dimension):
    """SQL for one metric, by one dimension, in a window."""
    m = METRICS[name]
    dim = m["dimensions"][dimension]
    return (f"select {dim} as {dimension}, "
            f"{m['numerator']} * 1.0 / {m['denominator']} as rate "
            f"from {m['from']} where {m['where']} "
            f"and {m['time']} >= ? and {m['time']} < ? "
            f"group by {dimension} order by {dimension}")


def answers(db):
    raw = dict(db.execute(RAW_SQL, WEEK).fetchall())
    sql = compile_metric("substitution_acceptance_rate", "pair")
    governed = dict(db.execute(sql, WEEK).fetchall())
    return raw, governed


def source():
    """How the metric appears in a receipt's knowing_what."""
    m = METRICS["substitution_acceptance_rate"]
    return {"id": "metric:substitution_acceptance_rate",
            "uri": "semantic://pronto/metrics/"
                   "substitution_acceptance_rate",
            "version": str(m["version"]),
            "retrieved_at": "2026-12-14T08:00:00Z",
            "authority": m["owner"],
            "sensitivity": "internal"}


def fingerprint():
    """Digest of the definition, so a silent edit shows."""
    return digest(METRICS["substitution_acceptance_rate"])


def below(rates):
    return [p for p, r in rates.items() if r < THRESHOLD]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    raw, governed = answers(load())
    print("Pick: which substitutions fell below 50% acceptance,")
    print(f"week of Dec 7 ({len(raw)} pairs offered)")
    print(f"{'pair':<31}{'raw SQL':>8}{'metric v3':>11}")
    for pair in raw:
        print(f"{pair:<31}{raw[pair]:>8.0%}{governed[pair]:>11.0%}")
    print("raw SQL would stop:")
    for p in below(raw):
        print(f"  {p}")
    print("governed metric stops:")
    for p in below(governed):
        print(f"  {p}")
    if argv:
        out = pathlib.Path(argv[0])
        out.mkdir(parents=True, exist_ok=True)
        (out / "metric-source.json").write_text(
            json.dumps(source(), indent=2) + "\n")
        print("wrote", out / "metric-source.json")


if __name__ == "__main__":
    main()

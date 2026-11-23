"""Versioned records, as the systems of record kept them (Ch 7).

Pronto's order and photo services keep every version of a record by
its ETag, and the policy knowledge base keeps every published
version. Replay asks for (record, version) and gets exactly what the
agent saw. The lab rebuilds the night's versions from its plan.
"""
from collector.night import conversations, stock
from pronto.world import DEFAULT_POLICY, MONDAY_POLICY, World


def snapshots():
    """{(source id, version): record} for the night and policies."""
    world = World()
    for c in conversations():
        stock(world, c)
    snaps = {}
    for records in (world.orders, world.photos):
        for rec in records.values():
            src = rec["source"]
            snaps[src["id"], src["version"]] = dict(rec)
    monday = {**DEFAULT_POLICY, **MONDAY_POLICY}
    for pol in (DEFAULT_POLICY, monday):
        src = pol["source"]
        snaps[src["id"], src["version"]] = dict(pol)
    return snaps

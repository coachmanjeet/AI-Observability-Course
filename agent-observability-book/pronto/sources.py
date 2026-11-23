"""Pronto's source catalog, as much of it as Chapter 6 needs.

A trace says which record an agent read and which version it was.
The catalog says where that record lives, who is its authority, how
sensitive it is, who wrote it (origin) and how far an agent may
rely on it (trust). Chapter 9 builds the full catalog.
"""
CATALOG = {
    "policy": {"uri": "kb://pronto/policies/{name}",
               "authority": "team:finance", "sensitivity": "internal",
               "origin": "pronto", "trust": "authoritative"},
    "order": {"uri": "orders://{name}",
              "authority": "system:orders",
              "sensitivity": "confidential",
              "origin": "pronto", "trust": "authoritative"},
    "photo": {"uri": "photos://{name}",
              "authority": "system:photos",
              "sensitivity": "confidential",
              "origin": "customer", "trust": "evidence"},
}


def describe(source_id):
    """Catalog entry for 'order:ord_5521', with its URI filled in."""
    kind, name = source_id.split(":", 1)
    entry = CATALOG.get(kind)
    if not entry:
        return {}
    return {**entry, "uri": entry["uri"].format(name=name)}

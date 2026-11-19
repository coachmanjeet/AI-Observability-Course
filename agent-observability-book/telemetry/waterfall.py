"""Prints a trace as a text waterfall, 64 columns wide (Chapter 4)."""
import sys

from telemetry import otlp

NAME, BAR = 29, 26


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def depth(span, by_id):
    d = 0
    while span["parent_id"] in by_id:
        span, d = by_id[span["parent_id"]], d + 1
    return d


def waterfall(spans):
    """One waterfall per trace, in the order the traces started."""
    traces = {}
    for s in spans:
        traces.setdefault(s["trace_id"], []).append(s)
    return "\n\n".join(_one(t) for t in traces.values())


def _one(spans):
    by_id = {s["span_id"]: s for s in spans}
    t0 = min(s["start"] for s in spans)
    total = max(s["end"] for s in spans) - t0
    chats = [s for s in spans if s["name"].startswith("chat ")]
    tools = [s for s in spans if s["name"].startswith("execute_tool")]
    tokens_in = sum(s["attributes"].get("gen_ai.usage.input_tokens", 0)
                    for s in chats)
    tokens_out = sum(s["attributes"].get("gen_ai.usage.output_tokens", 0)
                     for s in chats)
    lines = [f"trace {spans[0]['trace_id']}  {total / 1e9:.1f} s"]
    links = {link["trace_id"] for s in spans for link in s["links"]
             if link["trace_id"] != s["trace_id"]}
    lines += [f"  links to trace {t[:8]}" for t in sorted(links)]
    for s in spans:
        label = (" " * depth(s, by_id) + s["name"].replace(
            "execute_tool ", "tool "))[:NAME]
        a = min(BAR - 1, round((s["start"] - t0) / total * BAR))
        b = max(a + 1, round((s["end"] - t0) / total * BAR))
        bar = " " * a + "=" * (b - a) + " " * (BAR - b)
        mark = "!" if s["status"] == 2 else " "
        seconds = (s["end"] - s["start"]) / 1e9
        lines.append(f"{label:<{NAME}}|{bar}|{mark}{seconds:5.2f}")
    if chats:
        lines.append(f"{plural(len(chats), 'model call')}, "
                     f"{plural(len(tools), 'tool call')}, "
                     f"{tokens_in:,} tokens in, {tokens_out:,} out")
    return "\n".join(lines)


if __name__ == "__main__":
    print(waterfall(otlp.load(sys.argv[1])))

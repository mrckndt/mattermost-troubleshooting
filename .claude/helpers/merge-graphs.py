#!/usr/bin/env python3
"""Workaround for the upstream `graphify merge-graphs` CLI bug.

Behaviour matches what `graphify merge-graphs <inputs...> --out <output>`
would produce if the upstream bug were fixed:
- MultiGraph accumulator
- Per-input coercion to MultiGraph (cluster-only sometimes writes plain Graph)
- prefix_graph_for_global applied per input (each node gets a `repo` attribute)
- networkx node-link JSON output

Bug: the installed `graphify merge-graphs` initialises the accumulator as a
simple `Graph` while `prefix_graph_for_global` returns a `MultiGraph`, so
`networkx.compose` raises `All graphs must be graphs or multigraphs.`. See
`notes/graphify-merge-graphs-upstream-fix.md` for the upstream patch.

Invoke with the graphify-installed Python interpreter:

    GRAPHIFY_BIN=$(which graphify)
    PYTHON=$(head -1 "$GRAPHIFY_BIN" | cut -d' ' -f1 | sed 's/#!//')
    "$PYTHON" .claude/helpers/merge-graphs.py <inputs...> --out <output>

When the upstream patch lands in the installed graphify version, run
`graphify merge-graphs` directly on a few real inputs to confirm the bug is
fixed, then delete this file and replace every `merge-graphs.py` invocation
in `.claude/commands/*.md` with plain `graphify merge-graphs ...`.
"""

import json
import sys
from pathlib import Path

import networkx as nx
from networkx.readwrite import json_graph as jg

from graphify.build import prefix_graph_for_global


def main(argv: list[str]) -> int:
    args = argv[1:]
    if "--out" not in args:
        print("error: --out <path> is required", file=sys.stderr)
        return 2
    out_idx = args.index("--out")
    if out_idx + 1 >= len(args):
        print("error: --out requires a path argument", file=sys.stderr)
        return 2

    inputs = [Path(p) for p in args[:out_idx]]
    out_path = Path(args[out_idx + 1])

    if not inputs:
        print("error: at least one input graph.json is required", file=sys.stderr)
        return 2

    for gp in inputs:
        if not gp.exists():
            print(f"error: input not found: {gp}", file=sys.stderr)
            return 1

    merged = nx.MultiGraph()
    for gp in inputs:
        data = json.loads(gp.read_text(encoding="utf-8"))
        if "links" not in data and "edges" in data:
            data = dict(data, links=data["edges"])
        try:
            g = jg.node_link_graph(data, edges="links")
        except TypeError:
            g = jg.node_link_graph(data)
        if not g.is_multigraph():
            g = nx.MultiGraph(g)
        # `prefix_graph_for_global` uses the parent's parent dir name as the
        # repo prefix (e.g. graphs/<repo>/graphify-out/graph.json -> "<repo>").
        g = prefix_graph_for_global(g, gp.parent.parent.name)
        merged = nx.compose(merged, g)

    out_data = jg.node_link_data(merged, edges="links")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
    print(
        f"Merged {len(inputs)} graphs -> "
        f"{merged.number_of_nodes()} nodes, {merged.number_of_edges()} edges"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

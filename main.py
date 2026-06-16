"""CLI entry point for the Financial Fraud Detection & Investigation Engine."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from data_generator import generate_mock_transactions
from fraud_detector import FraudDetector, SharedIdentifierFinding


def _format_cycle(cycle: list[str]) -> str:
    return " -> ".join(cycle)


def _print_cli_report(
    cycles: list[list[str]],
    shared_identifiers: list[SharedIdentifierFinding],
) -> None:
    """Print a readable investigation report for terminal demos."""

    print("=" * 72)
    print("Financial Fraud Detection & Investigation Engine")
    print("=" * 72)

    print("\n1) Circular Transaction Findings")
    if cycles:
        for index, cycle in enumerate(cycles, start=1):
            involved_accounts = sorted(set(cycle))
            print(f"   [{index}] Path: {_format_cycle(cycle)}")
            print(f"       Flagged accounts: {', '.join(involved_accounts)}")
    else:
        print("   No circular transactions detected.")

    print("\n2) Shared Identifier Findings")
    if shared_identifiers:
        for index, finding in enumerate(shared_identifiers, start=1):
            print(
                f"   [{index}] {finding.identifier_type.upper()} hub: "
                f"{finding.identifier} ({finding.degree} linked accounts)"
            )
            print(f"       Accounts: {', '.join(finding.accounts)}")
    else:
        print("   No suspicious shared identifiers detected.")

    print("\nSummary")
    print(f"   Circular transaction loops: {len(cycles)}")
    print(f"   Shared identifier hubs:     {len(shared_identifiers)}")
    print("=" * 72)


def _save_flagged_network_plot(
    detector: FraudDetector,
    cycles: list[list[str]],
    shared_identifiers: list[SharedIdentifierFinding],
    output_path: Path,
) -> None:
    """Save a PNG visualization of only the flagged fraud subgraph."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    matplotlib_cache_dir = output_path.parent / ".matplotlib-cache"
    matplotlib_cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_cache_dir.resolve()))

    try:
        import matplotlib
        import matplotlib.pyplot as plt
        import networkx as nx
    except ImportError as exc:
        raise SystemExit(
            "Plotting requires optional dependencies. Run: pip install -r requirements.txt"
        ) from exc

    matplotlib.use("Agg", force=True)

    flagged_graph = detector.build_flagged_subgraph(cycles, shared_identifiers)
    if flagged_graph.number_of_nodes() == 0:
        print("No flagged network to visualize.")
        return

    node_colors = []
    for node_id, attributes in flagged_graph.nodes(data=True):
        node_type = attributes.get("node_type")
        if node_type == "account":
            node_colors.append("#d95f02")
        elif node_type in {"phone", "ip", "email", "device"}:
            node_colors.append("#1b9e77")
        else:
            node_colors.append("#7570b3")

    edge_colors = [
        "#e7298a"
        if attributes.get("relationship") == "TRANSACTION"
        else "#666666"
        for _, _, attributes in flagged_graph.edges(data=True)
    ]

    plt.figure(figsize=(12, 8))
    positions = nx.spring_layout(flagged_graph, seed=7, k=0.9)
    nx.draw_networkx_nodes(
        flagged_graph,
        positions,
        node_color=node_colors,
        node_size=1700,
        edgecolors="#222222",
        linewidths=0.8,
    )
    nx.draw_networkx_edges(
        flagged_graph,
        positions,
        edge_color=edge_colors,
        arrows=True,
        arrowsize=18,
        width=2.0,
        connectionstyle="arc3,rad=0.08",
    )
    nx.draw_networkx_labels(flagged_graph, positions, font_size=8, font_weight="bold")

    edge_labels = {
        (source, target): attributes.get("relationship", "")
        for source, target, attributes in flagged_graph.edges(data=True)
    }
    nx.draw_networkx_edge_labels(
        flagged_graph,
        positions,
        edge_labels=edge_labels,
        font_size=7,
    )

    plt.title("Flagged Fraud Network", fontsize=14, fontweight="bold")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()

    print(f"\nSaved flagged network visualization to: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run graph-based fraud detection on deterministic mock data."
    )
    parser.add_argument(
        "--min-shared-accounts",
        type=int,
        default=3,
        help="Minimum number of accounts sharing an identifier before it is flagged.",
    )
    parser.add_argument(
        "--max-cycle-length",
        type=int,
        default=6,
        help="Maximum account cycle length included in the report.",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Save a PNG visualization of the flagged fraud network.",
    )
    parser.add_argument(
        "--plot-path",
        type=Path,
        default=Path("outputs/flagged_fraud_network.png"),
        help="Where to save the fraud network visualization when --plot is used.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    edges = generate_mock_transactions()
    detector = FraudDetector(edges)

    cycles = detector.detect_circular_transactions(
        max_cycle_length=args.max_cycle_length
    )
    shared_identifiers = detector.detect_shared_identifiers(
        min_accounts=args.min_shared_accounts
    )

    _print_cli_report(cycles, shared_identifiers)

    if args.plot:
        _save_flagged_network_plot(detector, cycles, shared_identifiers, args.plot_path)


if __name__ == "__main__":
    main()

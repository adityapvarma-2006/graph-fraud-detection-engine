"""Mock financial graph data generator.

The generator returns simple edge dictionaries so the data is easy to inspect,
test, serialize, or replace with a real data source later.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from random import Random
from typing import Any


@dataclass(frozen=True)
class Edge:
    """A relationship between two graph nodes.

    Transactions are represented as account -> account edges.
    Identifiers are represented as account -> identifier edges.
    """

    source: str
    target: str
    relationship: str
    amount: float | None = None
    currency: str | None = None
    timestamp: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _iso_timestamp(base: datetime, minutes_offset: int) -> str:
    """Return a stable ISO-8601 UTC timestamp for deterministic demo data."""

    return (base + timedelta(minutes=minutes_offset)).isoformat()


def generate_mock_transactions(seed: int = 42) -> list[dict[str, Any]]:
    """Generate a small graph dataset with intentionally injected fraud.

    Injected patterns:
    1. Circular transaction: ACC-LAUNDER-001 -> 002 -> 003 -> 001
    2. Shared identifier: several accounts connected to the same phone and IP

    Args:
        seed: Random seed used for deterministic benign transaction generation.

    Returns:
        A list of edge dictionaries ready to load into FraudDetector.
    """

    rng = Random(seed)
    base_time = datetime(2026, 6, 16, 9, 0, tzinfo=timezone.utc)
    edges: list[Edge] = []

    legitimate_accounts = [f"ACC-REG-{idx:03d}" for idx in range(1, 11)]
    merchant_accounts = [f"MERCHANT-{idx:03d}" for idx in range(1, 5)]

    # Benign account-to-merchant payments. These make the graph realistic enough
    # for a demo without obscuring the intentionally injected fraud patterns.
    for idx, account in enumerate(legitimate_accounts):
        merchant = rng.choice(merchant_accounts)
        amount = round(rng.uniform(18.0, 420.0), 2)
        edges.append(
            Edge(
                source=account,
                target=merchant,
                relationship="TRANSACTION",
                amount=amount,
                currency="USD",
                timestamp=_iso_timestamp(base_time, idx * 7),
                metadata={"channel": rng.choice(["card", "ach", "wire"])},
            )
        )

    # Benign identifiers. Each legitimate account mostly has unique identifiers.
    for idx, account in enumerate(legitimate_accounts, start=1):
        edges.extend(
            [
                Edge(
                    source=account,
                    target=f"PHONE-555-01{idx:02d}",
                    relationship="USES_PHONE",
                    metadata={"identifier_type": "phone"},
                ),
                Edge(
                    source=account,
                    target=f"IP-203.0.113.{idx}",
                    relationship="USES_IP",
                    metadata={"identifier_type": "ip"},
                ),
            ]
        )

    # Injected fraud pattern 1: a circular transaction loop. In a real fraud
    # platform, this can indicate layering in money laundering.
    laundering_cycle = [
        ("ACC-LAUNDER-001", "ACC-LAUNDER-002", 9800.00),
        ("ACC-LAUNDER-002", "ACC-LAUNDER-003", 9750.00),
        ("ACC-LAUNDER-003", "ACC-LAUNDER-001", 9700.00),
    ]
    for offset, (source, target, amount) in enumerate(laundering_cycle, start=100):
        edges.append(
            Edge(
                source=source,
                target=target,
                relationship="TRANSACTION",
                amount=amount,
                currency="USD",
                timestamp=_iso_timestamp(base_time, offset),
                metadata={"injected_pattern": "circular_transaction"},
            )
        )

    # Injected fraud pattern 2: multiple distinct accounts share the same phone
    # and IP. This often points to synthetic identity rings or account farms.
    suspicious_accounts = [f"ACC-SYNTH-{idx:03d}" for idx in range(1, 6)]
    shared_phone = "PHONE-555-FRAUD"
    shared_ip = "IP-198.51.100.77"

    for idx, account in enumerate(suspicious_accounts, start=1):
        edges.extend(
            [
                Edge(
                    source=account,
                    target=shared_phone,
                    relationship="USES_PHONE",
                    metadata={
                        "identifier_type": "phone",
                        "injected_pattern": "shared_identifier",
                    },
                ),
                Edge(
                    source=account,
                    target=shared_ip,
                    relationship="USES_IP",
                    metadata={
                        "identifier_type": "ip",
                        "injected_pattern": "shared_identifier",
                    },
                ),
            ]
        )

    # A few transactions involving suspicious accounts make the final visualization
    # more useful for investigation.
    for idx, account in enumerate(suspicious_accounts, start=200):
        edges.append(
            Edge(
                source=account,
                target=rng.choice(merchant_accounts),
                relationship="TRANSACTION",
                amount=round(rng.uniform(500.0, 1500.0), 2),
                currency="USD",
                timestamp=_iso_timestamp(base_time, idx),
                metadata={"channel": "wallet"},
            )
        )

    return [edge.to_dict() for edge in edges]


if __name__ == "__main__":
    for edge in generate_mock_transactions():
        print(edge)

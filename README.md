# Financial Fraud Detection & Investigation Engine

A lightweight, interview-ready Python project that uses graph analytics to detect suspicious financial behavior. It models accounts, transactions, phone numbers, and IP addresses as a directed graph with `networkx`, then flags two common fraud patterns:

- **Circular transactions:** Account A sends money to B, B sends to C, and C sends back to A. This can indicate layering behavior in money laundering.
- **Shared identifiers:** Many distinct accounts use the same phone number or IP address. This can indicate synthetic identity rings, mule networks, or coordinated account farms.

This project is intentionally self-contained. It does not require Neo4j, TigerGraph, PostgreSQL, Kafka, or any external service, which makes it easy to explain, run, and modify during interviews.

## Why Graphs Are Ideal for Fraud Detection

Relational databases are excellent for storing transactions, accounts, and customer records, but fraud investigations often depend on relationship patterns rather than single rows. SQL can answer "what transactions did this account make?" very well, but it becomes more complex when the question is:

- Which accounts form a money movement loop?
- Which accounts are indirectly connected through the same phone, IP, device, or beneficiary?
- Which identifier behaves like a suspicious hub?
- What is the shortest investigative path between two entities?

Graphs make these questions natural. Accounts, merchants, IPs, phones, and devices become nodes. Transactions and identity links become edges. Once represented this way, fraud patterns can be discovered with standard graph algorithms such as DFS, cycle detection, connected components, centrality, and shortest paths.

## Project Structure

```text
financial-fraud-detector/
├── README.md
├── requirements.txt
├── data_generator.py
├── fraud_detector.py
└── main.py
```

## Installation

```bash
git clone <your-repo-url>
cd financial-fraud-detector
python -m venv .venv
```

Activate the virtual environment:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the Demo

Run the CLI report:

```bash
python main.py
```

Run the CLI report and save a PNG visualization of the flagged fraud network:

```bash
python main.py --plot
```

The visualization is saved to:

```text
outputs/flagged_fraud_network.png
```

You can tune detection thresholds:

```bash
python main.py --min-shared-accounts 4 --max-cycle-length 5 --plot
```

## Expected Output

The CLI prints:

- Circular transaction paths, such as `ACC-LAUNDER-001 -> ACC-LAUNDER-002 -> ACC-LAUNDER-003 -> ACC-LAUNDER-001`
- Shared phone/IP hubs, such as `PHONE-555-FRAUD` and `IP-198.51.100.77`
- A summary count of the flagged fraud patterns

## How It Works

### Data Generation

`data_generator.py` creates deterministic mock data:

- Normal account-to-merchant transactions
- Normal account-to-phone and account-to-IP relationships
- One injected circular transaction ring
- One injected shared phone number pattern
- One injected shared IP address pattern

The generator returns a list of edge dictionaries, which keeps the project simple and makes it easy to replace the mock source with a CSV, API response, database query, or streaming event source.

### Fraud Detection

`fraud_detector.py` loads edge dictionaries into a `networkx.DiGraph`.

The detector then uses two projections of the graph:

- A transaction-only account graph for cycle detection
- An identifier graph for finding high-degree phone/IP hubs

### Visualization

`main.py --plot` builds a smaller graph containing only flagged evidence and saves it with `matplotlib`. This keeps the visual investigation view focused instead of showing every benign node.

## Interview Talking Points

### 1. Why Graph Instead of Pure SQL?

Fraud is relationship-heavy. A single transaction may look normal, but the path across many accounts can reveal laundering. Graphs reduce the friction of asking path, cycle, neighborhood, and hub questions.

### 2. Cycle Detection Complexity

The circular transaction detector uses `networkx.simple_cycles`, which is based on Johnson's algorithm. Its worst-case complexity is:

```text
O((V + E) * (C + 1))
```

Where:

- `V` is the number of nodes
- `E` is the number of edges
- `C` is the number of cycles found

This is appropriate for a focused investigation graph or a filtered transaction window. In production, you would usually restrict the search by amount, time window, geography, customer risk score, hop count, or account cohort.

### 3. Shared Identifier Detection Complexity

Shared identifier detection scans relevant identifier edges once and groups accounts by target identifier.

```text
O(V + E)
```

This scales well and can be implemented in batch jobs, streaming jobs, or graph database queries.

### 4. Production Scaling Strategy

For a real system, this prototype can evolve into:

- A streaming ingestion layer for transactions and identity events
- A graph database or graph processing engine for large-scale traversal
- Incremental feature computation for high-degree identifiers and risky communities
- Model scoring that combines graph features with traditional ML features
- Case management outputs for fraud analysts

Useful graph features include:

- In-degree and out-degree
- Number of shared identifiers
- Cycle participation count
- Shortest path to known bad accounts
- PageRank or centrality
- Weakly connected component size
- Transaction velocity across neighborhoods

### 5. Why This Demo Is Useful

This project shows practical backend engineering instincts:

- Clean module boundaries
- Deterministic test data
- Replaceable data source shape
- Explainable algorithms
- CLI-first execution
- Optional visualization
- No heavyweight infrastructure required for the demo

## Next Improvements

- Add unit tests with `pytest`
- Load transactions from CSV or JSON
- Add account risk scoring
- Add connected component detection
- Export findings as JSON for an API or case management tool
- Add FastAPI endpoints for detection-as-a-service

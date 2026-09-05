Track: 8

# ChainAlert: Autonomous Supply Chain Disruption Response Engine

ChainAlert is an intelligent supply chain resilience platform built for enterprise supply chain operations. When unstructured disruption notices—such as carrier advisories, weather bulletins, port authority alerts, or supplier emails—arrive in prose, ChainAlert automatically extracts operational incident parameters, traverses the multi-tier supply chain dependency graph, traces downstream stockout risks down to finished goods and customer delivery dates, and generates ranked, actionable mitigation plans with explicit trade-off analysis.

Crucially, ChainAlert accurately identifies non-impacting events ("No impact") to prevent operational panic and false alarms.

---

## Key Features

1. **Unstructured Disruption Intake**: Ingests supplier emails, carrier advisories, weather alerts, and port status bulletins written in natural language.
2. **Deep Semantic Entity & Impact Extraction**: Powered by `gemini-2.5-flash-lite`, extracts geographic coordinates, port hubs, affected supplier nodes, component SKUs, and estimated disruption duration.
3. **Multi-Tier Graph Tracing**: Traverses relationships from Tier-1/Tier-2/Tier-3 suppliers through Bills of Materials (BOM), manufacturing assembly hubs, on-hand buffer inventories, and active transit shipments.
4. **Days-to-Stockout & Financial Exposure Analytics**: Quantifies whether existing buffer stocks can bridge the disruption window or whether factory lines will idle, calculating total contract penalty exposure and revenue at risk.
5. **Ranked Mitigation Strategies with Trade-offs**: Generates concrete response strategies (e.g. Expedited Air Freight, Tier-2 Supplier Rerouting, Buffer Reallocation) ranked by business priority with trade-offs across Cost Delta, Delay Reduction, SLA Risk, and Execution Complexity.
6. **Negative Impact Filtering**: Intelligently dismisses irrelevant alerts (e.g. perishables/flower cargo delays when shipping precision industrial components) with high-confidence "No Impact" verdicts.
7. **Instant Startup with Cached Embeddings**: Includes precomputed supplier and transit routing vector representations (`data/precomputed_embeddings.json`) ensuring sub-second startup time.

---

## Supply Chain Architecture & Data

ChainAlert models an advanced industrial electronics and robotics manufacturer with global operations:

- **Suppliers (`data/suppliers.json`)**:
  - `SUP-001`: Precision Microelectronics Corp (Taoyuan / Kaohsiung, Taiwan) — Tier-1 Microcontrollers & AI accelerators.
  - `SUP-002`: Shenzhen Polymer Optics (Shenzhen, China) — Tier-2 Optical sensor housings.
  - `SUP-003`: Rotterdam Specialty Alloys (Rotterdam / Duisburg, Netherlands/Germany) — Tier-2 Structural titanium alloys.
  - `SUP-004`: Kyoto High-Purity Silicon (Kyoto / Japan) — Tier-3 Semiconductor boules.
  - `SUP-005`: Bavaria Precision Hydraulics (Munich, Germany) — Tier-1 Actuator manifolds.
  - `SUP-006`: Atlas Transpacific Freight (Global Ocean Carrier) — Major maritime transit lanes.
  - Backup suppliers with pre-negotiated activation lead times, tooling fees, and capacity allocations.

- **Inventory & Routes (`data/inventory_and_routes.json`)**:
  - Assembly Hubs: Austin Assembly Plant (USA) and Munich Manufacturing Facility (Germany).
  - Products: `PROD-APEX` (Industrial Drone System), `PROD-SENTINEL` (Hospital Diagnostic Imaging Scanner), `PROD-VORTEX` (Smart Grid Inverter).
  - Transit Shipments: Active Bills of Lading / PO shipments currently on ocean or air transit routes with real-time status.

- **Sample Disruption Scenarios (`data/sample_notices.json`)**:
  1. *Super Typhoon Kaemi (Taiwan)*: Port closure, fab shutdown, affecting microcontrollers (Critical impact on Austin hub).
  2. *Rhine River Low Water Gauge (Germany)*: Barge draft restrictions delaying alloy shipments to Munich.
  3. *Red Sea / Suez Canal Maritime Rerouting*: +14 day transit delay and bunker fuel surcharge for European shipments.
  4. *Chilean Lithium Mine Wildcat Strike*: Upstream raw material disruption requiring secondary source activation.
  5. *Rotterdam Floral Cargo Hold (Negative Control)*: Delays affecting perishable flower shipments (Zero company impact).

---

## Quickstart

### Prerequisites
- Python 3.11+
- Google Gemini API Key (`GEMINI_API_KEY`)

### Setup and Running

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set Gemini API key
export GEMINI_API_KEY="your-gemini-api-key"

# 3. Start application
python app.py
```

The application starts immediately on **http://localhost:8000** serving both the interactive dashboard UI and the REST API.

---

## API Endpoints

- `GET /`: Interactive web dashboard.
- `GET /api/status`: System health, total supplier count, BOM parts count, and active transit shipments.
- `GET /api/samples`: Sample disruption notices for one-click testing.
- `GET /api/network`: Multi-tier graph nodes and edges for supply chain network visualization.
- `POST /api/analyze`: Analyze an unstructured disruption notice text and receive graph impact analysis and ranked mitigation plans.

---

## Demo Video

Walkthrough and demonstration: [https://youtu.be/k8mQ1vF9e2A](https://youtu.be/k8mQ1vF9e2A)

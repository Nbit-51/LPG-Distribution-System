# Smart LPG Distribution Management System

**Priority-Based Cylinder Allocation with Anti-Starvation Guarantees**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/framework-FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![MySQL 8.0](https://img.shields.io/badge/database-MySQL%208.0-4479A1.svg)](https://mysql.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A full-stack allocation engine that replaces First-Come, First-Served (FCFS) queuing in India's LPG distribution infrastructure with a priority-aware, starvation-free, shortage-splitting algorithm. Designed for compliance with PMUY (Pradhan Mantri Ujjwala Yojana) and NFSA (National Food Security Act) mandates.

---

## Problem

India operates 314 million LPG connections through ~25,000 distributors, all using FCFS allocation. This model has three structural failures under shortage conditions:

| Failure Mode | Description | Consequence |
|---|---|---|
| **No priority differentiation** | A 10-cylinder commercial order is processed identically to a 1-cylinder household refill | Domestic consumers starved during shortages |
| **All-or-Nothing blocking** | If remaining stock < order size, the entire order is skipped | Cylinders sit idle in warehouses while consumers wait |
| **Zero crisis response** | No mechanism to restrict commercial consumption during emergencies | Governance failure during floods, supply disruptions |

## Solution

The Smart Priority Engine introduces four algorithmic improvements over FCFS, all operating at the same O(n log n) time complexity:

### 1. Three-Tier Priority Classification

Orders are sorted by consumer class before processing. Priority ranks are configurable via the `priority_policies` table.

```
Domestic    → rank 1 (highest)    # Household cooking — no alternative fuel
Essential   → rank 2              # Hospitals, schools — critical services  
Commercial  → rank 3 (lowest)     # Hotels, restaurants — alternative fuels available
```

### 2. Pro-Rata Shortage Splitting

FCFS skips orders it cannot fully satisfy. Our engine delivers partial fulfillment and auto-creates backorders:

```
FCFS:    stock=3, order=5  →  skip entirely     →  3 cylinders idle
Smart:   stock=3, order=5  →  deliver 3, backorder 2  →  0 cylinders idle
```

### 3. Anti-Starvation Ageing (Liveness Guarantee)

A dynamic priority score prevents indefinite starvation of lower-priority consumers:

```
effective_score = base_rank − (α × waiting_days)     where α = 0.02
```

A commercial consumer (rank 3) achieves domestic-level priority (rank 1) after `(3−1)/0.02 = 100 days`. This bound is configurable via the escalation coefficient α.

**Proof**: For any consumer with base rank `r_max`, the maximum wait time before achieving rank `r_min` priority is `(r_max − r_min) / α` days. This is finite and bounded, satisfying the liveness property.

### 4. Crisis Mode

One-click activation freezes commercial allocation and applies configurable per-tier caps:

| Consumer Type | Normal Max | Crisis Max |
|---|---|---|
| Domestic | 6 | 2 (rationed) |
| Essential | 8 | 4 |
| Commercial | 15 | 0 (frozen) |

---

## Performance

Benchmarked using the built-in simulation endpoint (`POST /allocation/simulate`) which runs both algorithms on identical input:

### Scenario: 8 cylinders available, 11 demanded (5 domestic + 6 commercial)

| Metric | FCFS | Smart Priority | Delta |
|---|:---:|:---:|:---:|
| Cylinders allocated | 5 | **8** | +60% |
| Domestic served | 0 | **5** | +5 |
| Idle stock | 3 | **0** | −100% |
| Utilization | 62.5% | **100%** | +37.5 pp |

### Aggregated (6 test scenarios)

| Metric | FCFS | Smart | Improvement |
|---|:---:|:---:|:---:|
| Stock utilization | 67.3% | 95.8% | +28.5 pp |
| Domestic protection rate | 41.2% | 97.6% | +56.4 pp |
| Idle stock per run | 4.2 cyl | 0.3 cyl | −92.9% |
| Orders served (full + partial) | 58.3% | 91.7% | +33.4 pp |
| Time complexity | O(n log n) | O(n log n) | Equal |

---

## Architecture

Three-tier design with 11 independent backend modules:

```
Presentation    HTML5/CSS3/JS — Admin Dashboard, Consumer Portal, 
                Delivery Portal, Algorithm Playground

Application     FastAPI (Python) — 11 modules, JWT auth, Pydantic validation
                ┌──────────────────────────────────────────────────┐
                │ auth · consumers · agencies · bookings · supply  │
                │ allocation · delivery_agents · qr · invoices     │
                │ admin · support                                  │
                └──────────────────────────────────────────────────┘

Data            MySQL 8.0 — 10 tables, connection pooling (pool_size=10)
                consumers · agencies · bookings · supply_stock ·
                allocations · priority_policies · crisis_events ·
                delivery_assignments · invoices · shortage_alerts
```

---

## Features

**Core Engine**
- Priority-based allocation with dynamic scoring and anti-starvation ageing
- Pro-rata shortage splitting with automatic backorder creation
- Crisis mode with per-tier configurable cylinder caps
- Shortage detection and alert system

**Distribution Lifecycle**
- Consumer registration with Aadhaar/KYC verification
- Booking management with priority queue visualization
- Supply stock intake and batch-level tracking (FIFO depletion)
- Delivery agent assignment with geographic route clustering
- QR code generation and scan-to-verify delivery confirmation
- GST-compliant invoice generation with payment tracking

**Operations**
- Algorithm Playground — sandbox environment for policy testing with 6 preset scenarios and custom data entry
- Real-time dashboard with KPI monitoring
- Demand vs. supply analytics and reporting
- Support ticket system

---

## Project Structure

```
├── app/
│   ├── main.py                  # App initialization, CORS, route registration
│   ├── config.py                # Environment configuration (pydantic-settings)
│   ├── database.py              # MySQL connection pool, query executor
│   ├── allocation/
│   │   ├── routes.py            # /run/{id}, /simulate, /crisis endpoints
│   │   └── service.py           # Core allocation algorithm
│   ├── auth/                    # JWT authentication
│   ├── consumers/               # Consumer CRUD, KYC
│   ├── agencies/                # Agency management
│   ├── bookings/                # Booking lifecycle, priority queue
│   ├── supply/                  # Stock intake and tracking
│   ├── delivery_agents/         # Assignment, route clustering
│   ├── qr/                      # QR generation and verification
│   ├── invoices/                # GST invoice generation
│   ├── admin/                   # Dashboard overview API
│   └── support/                 # Grievance ticket system
├── static/
│   ├── css/main.css             # Design system
│   ├── js/utils.js              # API client, auth, sidebar
│   ├── js/layout.js             # Sidebar component
│   ├── dashboard.html           # Admin dashboard
│   ├── simulator.html           # Algorithm Playground
│   ├── consumer.html            # Consumer self-service portal
│   └── ...                      # 12 additional pages
├── docs/
│   └── VTU_Project_Report.md    # Full academic report
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup

### Prerequisites

- Python 3.10+
- MySQL 8.0+

### Installation

```bash
git clone https://github.com/Nbit-51/LPG-Distribution-System.git
cd LPG-Distribution-System

pip install -r requirements.txt
```

### Configuration

Create `.env` in the project root:

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=lpg_distribution
DB_USER=root
DB_PASSWORD=<your_password>
SECRET_KEY=<your_secret>
```

### Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Access

| Interface | URL |
|---|---|
| Admin Dashboard | `http://localhost:8000/dashboard` |
| Consumer Portal | `http://localhost:8000/consumer-portal` |
| Algorithm Playground | `http://localhost:8000/simulator-page` |
| API Documentation | `http://localhost:8000/docs` |

---

## API Reference

Interactive Swagger documentation available at `/docs`. Key endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/login` | JWT authentication |
| `GET` | `/consumers/` | List consumers (paginated) |
| `POST` | `/bookings/` | Create booking |
| `GET` | `/bookings/priority-queue` | View priority-sorted queue |
| `POST` | `/allocation/run/{agency_id}` | Execute allocation engine |
| `POST` | `/allocation/simulate` | Run FCFS vs Smart comparison |
| `POST` | `/allocation/crisis/{id}/activate` | Activate crisis mode |
| `POST` | `/allocation/crisis/{id}/resolve` | Deactivate crisis mode |
| `GET` | `/allocation/shortage/{agency_id}` | Check shortage status |
| `POST` | `/qr/verify` | Verify delivery QR code |
| `POST` | `/invoices/generate` | Generate GST invoice |
| `GET` | `/admin/overview` | Dashboard statistics |

---

## Policy Context

This system implements allocation policies aligned with:

- **Pradhan Mantri Ujjwala Yojana (PMUY)** — Priority access for 9.6 crore BPL household connections
- **National Food Security Act (NFSA)** — Domestic consumer priority during essential commodity shortages
- **Karnataka State Food & Civil Supplies Department** — Emergency distribution protocols for flood response (2019, 2023 Karnataka floods)

---

## Tech Stack

| Component | Technology |
|---|---|
| Backend | FastAPI, Python 3.10+, Pydantic v2, PyJWT |
| Database | MySQL 8.0, mysql-connector-python, connection pooling |
| Frontend | HTML5, CSS3, Vanilla JavaScript, Tabler Icons, Inter font |
| QR System | qrcode, Pillow |
| Server | Uvicorn (ASGI) |

---

## License

MIT

---

## Contributors

| Name | USN |
|---|---|
| | |
| | |
| | |
| | |

# Alpine Lambda Trade (ALT) 🏔️

![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![Terraform](https://img.shields.io/badge/terraform-%235835CC.svg?style=flat&logo=terraform&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-%23FF9900.svg?style=flat&logo=amazon-aws&logoColor=white)
![Snowflake](https://img.shields.io/badge/Snowflake-%2329B5E8.svg?style=flat&logo=snowflake&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-%23FF694B.svg?style=flat&logo=dbt&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-%23F46800.svg?style=flat&logo=grafana&logoColor=white)

**High-Throughput Lambda Architecture (Batch + Speed layers) with AWS & Snowflake.**

ALT is a high-frequency crypto analytics data platform built using a Lambda Architecture. It consumes real-time WebSocket feeds, simultaneously feeding a **Data Lake (AWS S3)** for historical archiving and a **Speed Layer (AWS SQS FIFO + Lambda)** with sub-second latency for market anomaly detection, all consolidated within **Snowflake**.

---

## 📑 Table of Contents

* [Business Value & Problem Solving](#-business-value--problem-solving)
* [Technical Architecture & Data Flow](#️-technical-architecture--data-flow)
* [Tech Stack Standards](#️-tech-stack-standards)
* [Grafana Observability & Dashboards](#-grafana-observability--dashboards)
* [Deep Dive: Implementation & Governance](#-deep-dive-implementation--governance)
* [Repository Structure](#-repository-structure)
* [Getting Started & Execution Guide](#-getting-started--execution-guide)

---

## 💡 Business Value & Problem Solving

This architecture directly addresses the three major challenges of financial data pipelines:

### 🎯 P1: Slippage Risk & Volatility Detection (< 1s)
* **Problem:** In high-frequency trading, a 2% price shift in 60 seconds can invalidate an execution strategy.
* **Solution ALT:** The **Speed Layer** (SQS FIFO -> AWS Lambda) computes Exponential Moving Averages (EMA) and Bollinger Bands in real-time using a "warm start" state cache. Volatility spikes (`SPIKE_DETECTED`) are written directly to Snowflake in under a second.

### 📜 P2: Auditability & Single Source of Truth (Historical)
* **Problem:** Real-time streams suffer from re-deliveries, out-of-order events, and corrupted data, making backtests unreliable.
* **Solution ALT:** The **Batch Layer** (S3 Parquet -> Snowpipe -> dbt Core) guarantees immutable storage and strict deduplication via analytical window functions in incremental dbt models (Silver layer):
```sql
  SELECT * FROM (
      SELECT *, ROW_NUMBER() OVER (PARTITION BY trade_id ORDER BY trade_timestamp DESC) as rn
      FROM {{ ref('stg_trades') }}
  ) WHERE rn = 1

```

### 📊 P3: Live Portfolio Valuation & P&L (Up-to-the-millisecond)

* **Problem:** Portfolio managers often experience a 15-minute delay in P&L valuation.
* **Solution ALT:** The **Serving Layer** (`GOLD.VW_REALTIME_PORTFOLIO`) performs a strategic fusion (`UNION ALL`) between consolidated historical transactions and real-time streams.

---

## 🏗️ Technical Architecture & Data Flow

All infrastructure is provisioned as Infrastructure as Code (IaC) via **Terraform** adhering to least-privilege principles and cost governance.

---

## 🛠️ Tech Stack Standards

* **Language & Runtime:** Python 3.12, Asyncio, `ccxt.pro` (WebSockets), Pydantic, Boto3.
* **Infrastructure as Code (IaC):** Terraform (AWS & Snowflake Provider).
* **Batch Ingestion & Storage:** AWS S3 (Snappy Parquet compression), Snowpipe SQS auto-ingest.
* **Streaming & Event-Driven:** AWS SQS FIFO (Redrive Policy & DLQ), AWS Lambda.
* **Data Warehouse & Transformations:** Snowflake (`BRONZE`, `SILVER`, `GOLD`), dbt Core 1.x (Incremental models, Schema constraints & Freshness checks).
* **Orchestration & Containerization:** Kestra, Docker Compose (PostgreSQL, Kestra, Grafana).
* **Monitoring & Visualization:** Streamlit (Altair charts), Grafana (CloudWatch & Snowflake Datasources).
* **Testing & Quality:** Pytest, Moto (AWS Mocking).

---

## 📊 Grafana Observability & Dashboards

The project includes provisioned Grafana data sources and pre-built dashboards (`grafana/`) to monitor pipeline health in real time:

```text
+-------------------------------------------------------------------------+
|                  ALT PLATFORM OBSERVABILITY DASHBOARD                   |
+-----------------------------+-------------------------------------------+
| [AWS CloudWatch Datasource] | • Lambda Ingestion Latency (< 500ms)      |
|                             | • SQS FIFO Queue Depth & DLQ Message Rate |
|                             | • Circuit-Breaker Failover Events         |
+-----------------------------+-------------------------------------------+
| [Snowflake Datasource]      | • Snowpipe Ingestion Status & Row Counts  |
|                             | • Virtual Warehouse Credit Consumption    |
|                             | • Real-time P&L Query Execution Times     |
+-----------------------------+-------------------------------------------+

```

---

## ⚙️ Deep Dive: Implementation & Governance

### 1. Resilient Ingestion: Multi-Exchange Circuit-Breaker

The producer (`src/producer/exchange_stream.py`) handles WebSocket connection drops automatically. Upon repeated failures on the primary exchange (e.g., Binance), it transparently fails over to a secondary exchange (Kraken, Coinbase) and triggers a Slack alert.

### 2. FinOps & Cost Governance

* **SQS FIFO Migration:** Replaced permanent Kinesis shards with an on-demand SQS FIFO queue.
* **Snowflake Auto-Suspend:** The `ALT_WH` Virtual Warehouse (X-Small size) automatically suspends after **60 seconds** of inactivity.
* **Parquet Format & Partitioning:** S3 storage optimized under path `ticker/YYYY/MM/DD/HH/trades_[timestamp].parquet` to minimize Snowpipe query scan costs.

### 3. Observability & Dead Letter Queue (DLQ)

If an SQS message fails processing 3 times in the Speed Layer Lambda, it routes to `alt-ticker-dlq.fifo`. The Streamlit dashboard polls SQS DLQ metrics in real-time and renders system alerts if any records encounter failures.

---

## 📁 Repository Structure

```text
alpine-lambda-trade/
├── Makefile                        # Command center (init, apply, run, test)
├── docker-compose.yml              # Kestra, Postgres & Grafana stack
├── infra/                          # Terraform modules (AWS & Snowflake)
│   ├── providers.tf
│   ├── s3.tf                       # Bucket & Snowpipe notifications
│   ├── sqs.tf                      # FIFO Queue & Dead Letter Queue
│   ├── lambda.tf                   # Speed Layer Lambda function
│   ├── snowflake.tf                # DB, Schemas, Warehouse & RBAC Roles
│   ├── iam_producer.tf             # Producer IAM policies
│   └── iam_snowflake.tf            # Storage Integration IAM
├── kestra/                         # Orchestration workflows
│   └── flows/
│       └── alpine_hourly_flow.yaml
├── grafana/                        # Provisioned Dashboards & Datasources
├── src/
│   ├── producer/                   # WebSocket Ingestion (CCXT, S3 Buffer, SQS)
│   ├── speed_layer/                # AWS Lambda (EMA, Bollinger, Snowflake Direct Sink)
│   ├── batch_layer/                # dbt project (Staging, Incremental Silver, Gold Views)
│   └── serving_layer/              # Real-Time Streamlit Application
└── tests/                          # Pytest suite (Moto S3 & SQS mocks)

```

---

## 🚀 Getting Started & Execution Guide

### Prerequisites & Cloud Authentication

Before running Terraform, you must configure authentication for both AWS and Snowflake. To adhere to the principle of least privilege and ensure proper auditability, **dedicated technical service accounts** should be used rather than personal accounts.

#### 1. AWS Authentication (Service Account / IAM Profile)

Configure a dedicated IAM user (`alt-terraform-deployer`) with permissions restricted to S3, SQS, Lambda, IAM, and CloudWatch, or configure via an AWS CLI profile:

```bash
aws configure --profile alt-terraform
# Or export environment variables for the deployment session:
export AWS_ACCESS_KEY_ID="your_service_account_access_key"
export AWS_SECRET_ACCESS_KEY="your_service_account_secret_key"
export AWS_DEFAULT_REGION="eu-north-1"

```

#### 2. Snowflake Provider Environment Variables (Service User)

Create a dedicated technical user (e.g., `ALT_TERRAFORM_USER`) with sufficient administrative privileges (`ACCOUNTADMIN` or `SYSADMIN`/`SECURITYADMIN`) to bootstrap the database, warehouse, and RBAC roles:

```sql
CREATE USER alt_terraform_user 
  PASSWORD='<secure_password>' 
  DEFAULT_WAREHOUSE='ALT_WH' 
  COMMENT='Service account for Terraform infrastructure deployment';
GRANT ROLE ACCOUNTADMIN TO USER alt_terraform_user;

```

Then, configure your Terraform variables via `infra/terraform.tfvars`:

```hcl
snowflake_account  = "org-account_identifier"
snowflake_user     = "alt_terraform_user"
snowflake_password = "your_secure_password"
snowflake_role     = "ACCOUNTADMIN"
snowflake_warehouse = "ALT_WH"

```

---

### Step-by-Step Execution

### 1. Environment Initialization

```bash
# Copy and configure the application runtime environment file
cp .env.example .env

# Copy and configure Terraform variables for infrastructure deployment
cp infra/terraform.tfvars.example infra/terraform.tfvars

```

### 2. Infrastructure Deployment (Terraform)

```bash
make init
make apply

```

### 3. Launch Local Services & Pipeline

```bash
# Start orchestration & monitoring services (Kestra & Grafana)
docker-compose up -d

# Start the WebSocket data producer
make run-producer

# Run dbt transformations (Silver & Gold layers)
make dbt-run

# Launch the Streamlit Dashboard
make run-dashboard

```

### 4. Unit Testing

```bash
pytest

```

---

*Developed by Michael GARCIA (Alpine Data) — Engineered for Scale, FinOps Performance, and Resilience.*


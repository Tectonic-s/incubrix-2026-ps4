# IncuBrix 2027 — PS4: Sources, Licenses & Provenance

This document details all external libraries, tools, frameworks, and datasets utilized in the **IncuBrix 2027 PS4 — Long-Tail Destination Network Service**, verifying compliance with commercial-use standards and assessment integrity.

---

## 1. Software Dependencies & Libraries

All runtime and development dependencies were selected under permissive commercial-use open source licenses (MIT, Apache 2.0, BSD-3-Clause). None impose copyleft viral obligations (GPL/AGPL) on proprietary consumer applications, nor do any prohibit commercial utilization.

| Library / Package | Version | License | Primary Purpose in Project | Source / Repository |
| :--- | :--- | :--- | :--- | :--- |
| **Python** | 3.14.0+ | PSF License | Runtime environment & core execution engine | https://python.org |
| **FastAPI** | 0.115.11 | MIT | Web framework for asynchronous REST API endpoints | https://github.com/tiangolo/fastapi |
| **Uvicorn** | 0.34.0 | BSD-3-Clause | ASGI production HTTP server implementation | https://github.com/encode/uvicorn |
| **Pydantic** | 2.10.6 | MIT | Data parsing, validation, and schema definitions | https://github.com/pydantic/pydantic |
| **HTTPX** | 0.28.1 | BSD-3-Clause | Asynchronous HTTP client for platform dispatch | https://github.com/encode/httpx |
| **PyYAML** | 6.0.2 | MIT | Connector manifest parsing & YAML serialisation | https://github.com/yaml/pyyaml |
| **Boto3** | 1.37.9 | Apache 2.0 | S3/MinIO compatible object storage integration | https://github.com/boto/boto3 |
| **python-multipart** | 0.0.20 | Apache 2.0 | Multipart form-data handling for catalogue uploads | https://github.com/Kludex/python-multipart |
| **Jinja2** | 3.1.6 | BSD-3-Clause | Dynamic template rendering for discussion framing | https://github.com/pallets/jinja |
| **openpyxl** | 3.1.5 | MIT | Excel workbook automation for assessment forms | https://foss.heptapod.net/openpyxl/openpyxl |
| **pytest** | 8.3.5 | MIT | Automated testing framework | https://github.com/pytest-dev/pytest |
| **pytest-asyncio**| 0.25.3 | Apache 2.0 | Asynchronous test execution runner for pytest | https://github.com/pytest-dev/pytest-asyncio |

---

## 2. Infrastructure & Supporting Tools

| Infrastructure / Tool | Version | License | Usage in Project |
| :--- | :--- | :--- | :--- |
| **Docker Engine** | 24.0+ | Apache 2.0 | Containerisation runtime |
| **Docker Compose** | 2.20+ | Apache 2.0 | Multi-container orchestration (Service, MinIO, Ghost, Mock Server) |
| **SQLite** | 3.45+ | Public Domain (Blessing) | Embedded relational database with WAL mode |
| **MinIO** | RELEASE.2024+ | AGPLv3 (Standalone Container) | Local S3 object store for dev/testing (unmodified container) |
| **Ghost CMS** | 5-alpine | MIT | Reference test target for headless CMS publishing |

*Note on MinIO:* MinIO is executed strictly as an isolated, unmodified external container service over standard S3 network APIs via Boto3. No MinIO source code is bundled, linked, or incorporated into the IncuBrix service codebase.

---

## 3. Dataset Provenance & Synthesis

### 3.1 Real Destination Catalogue (`data/real_catalogue_150.csv`)
- **Origin:** Hand-curated and researched publicly accessible developer forums, federated communities, and publishing destinations across AI, video engineering, SaaS, creator economy, and tech founders.
- **License / Terms:** Public metadata (names, URLs, categories, platform types). Does not scrape proprietary or gated private community data.
- **Size:** 155 destination rows.
- **Fields:** `id`, `name`, `platform_key`, `url`, `category`, `audience_relevance`, `frequency_cap`, `status`, `health_score`.

### 3.2 Benchmark Synthetic Dataset (`data/synthetic_1000_destinations.csv`)
- **Origin:** Synthetically generated deterministic dataset created for high-throughput import benchmarking, deduplication verification, and row-level error handling.
- **Size:** 1,000 rows with intentional edge cases (duplicate hostnames, missing URLs, unsupported platforms).
- **License:** CC0 Public Domain (Created specifically for this project).

### 3.3 Recommendation Ground Truth Dataset (`data/labeled_recommendation_eval.json`)
- **Origin:** Curated ground truth mapping 3 distinct content types (developer tutorial, AI research whitepaper, founder business essay) to ideal destination IDs within the 155-destination catalogue.
- **License:** CC0 Public Domain (Created specifically for recommendation algorithm benchmarking).

---

## 4. Assessment Integrity & Commercial Rights Confirmation

- **No Proprietary Code:** All source code in `src/`, `tests/`, and `test_pack/` was authored specifically for the IncuBrix 2027 PS4 assessment or generated via supervised AI pair-programming.
- **No Third-Party Outreach:** In strict accordance with the assessment instructions, no live prospect communities, real forum moderators, or external partners were spammed or contacted. Real platform testing was either conducted against local mock instances or authorized test developer sandboxes.
- **No Private Credentials:** No real production secrets, API tokens, or proprietary credentials are committed to this repository. All credentials use environment variables or test sandboxes.

# IncuBrix 2027 — PS4: Demo Video Runbook

> **Copy-Pastable Command Runbook for Recording the 7-Minute Demo**  
> *Target Duration: 7m 00s to 7m 30s (Max allowed: 8m 00s)*  
> *Format: Single-take unedited video (terminal commands + browser walkthrough)*

---

## 🛠️ Pre-Recording Setup

1. **Activate Virtualenv:**
   ```bash
   source .venv/bin/activate
   ```
2. **Verify Server is Running on Port 8001:**
   ```bash
   curl -s http://localhost:8001/health | jq .
   ```
   *(If not running, start it in a separate terminal tab: `.venv/bin/uvicorn src.api.app:app --host 0.0.0.0 --port 8001`)*
3. **Open Browser:** Tab at `http://localhost:8001/` (Command Center UI).
4. **Open Submission Form:** `IncuBrix_Assessment_4_Distribution_Long_Tail_Destination_Network_Submission_Form.xlsx`.

---

## 📋 Step-by-Step Execution Runbook

---

### Step 1: Health & Readiness Check
**Action:** Run health endpoint in terminal.

```bash
curl -s http://localhost:8001/health | jq .
```

**Expected Output:**
```json
{
  "status": "healthy",
  "service": "incubrix-distribution-service",
  "version": "1.0.0",
  "simulation_mode": true
}
```

---

### Step 2: Automated Test Suite (42/42 Tests)
**Action:** Execute entire test suite in terminal.

```bash
DATABASE_URL=sqlite:///./test_clean.db .venv/bin/pytest -v
```

**Expected Output:**
```text
tests/test_catalogue_import.py ... PASSED
tests/test_certification_harness.py ... PASSED
tests/test_connectors_contract.py ..... PASSED
tests/test_e2e_full_flow.py . PASSED
tests/test_hard_cases.py ....... PASSED
tests/test_integration_standard.py ........ PASSED
tests/test_quirks_and_features.py ...... PASSED
tests/test_rules_engine.py .... PASSED
tests/test_tailoring_recommender.py ..... PASSED
======================== 42 passed in 0.94s ========================
```

---

### Step 3: Asynchronous Publishing & Safe Retries (Idempotency)

#### 3A. Dispatch a New Post (Returns HTTP 202 Accepted)
```bash
curl -X POST http://localhost:8001/api/v1/publish \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-video-key-hf" \
  -d '{
    "destination_id": "Hugging Face Community",
    "rendition": {
      "title": "Scaling Distributed Pipelines in 2027",
      "body": "A practical guide to worker queues and retry backoffs.",
      "tags": ["python", "architecture"],
      "has_ai_disclosure": true,
      "is_promotional": false
    }
  }' | jq .
```

**Expected Output:**
```json
{
  "job_id": "job_...",
  "status": "queued",
  "progress": 0,
  "result_links": null,
  "error": null
}
```

#### 3B. Re-Send the Exact Same Request (Proves Idempotency)
```bash
curl -X POST http://localhost:8001/api/v1/publish \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-video-key-hf" \
  -d '{
    "destination_id": "Hugging Face Community",
    "rendition": {
      "title": "Scaling Distributed Pipelines in 2027",
      "body": "A practical guide to worker queues and retry backoffs.",
      "tags": ["python", "architecture"],
      "has_ai_disclosure": true,
      "is_promotional": false
    }
  }' | jq .
```

**Expected Output:** Returns the exact same `job_id` without creating a duplicate job or post.

#### 3C. Poll Job Status & Output Manifest
*(Replace `<JOB_ID>` with the `job_id` returned from Step 3A)*

```bash
curl -s http://localhost:8001/api/v1/jobs/<JOB_ID> | jq .
```

**Expected Output:**
```json
{
  "job_id": "job_...",
  "status": "succeeded",
  "progress": 100,
  "result_links": {
    "live_url": "https://discourse.example.com/t/...",
    "manifest_url": "/api/v1/storage/...",
    "destination_name": "Hugging Face Community",
    "tailored_rendition": {
      "title": "What are your thoughts on: Scaling Distributed Pipelines in 2027?..."
    }
  },
  "error": null
}
```

---

### Step 4: Brand Safety & Policy Interception (Frequency Cap Violation)

#### 4A. Dispatch a Second Post (Violates 1/7d Frequency Cap)
```bash
curl -X POST http://localhost:8001/api/v1/publish \
  -H "Content-Type: application/json" \
  -d '{
    "destination_id": "OpenAI Developer Community",
    "rendition": {
      "title": "Violating Frequency Cap: Rapid Succession Post",
      "body": "This post violates community cooldown rules.",
      "tags": ["test"],
      "has_ai_disclosure": true,
      "is_promotional": false
    }
  }' | jq .
```

#### 4B. Check Error Diagnostics
*(Replace `<JOB_ID>` with the `job_id` returned from Step 4A)*

```bash
curl -s http://localhost:8001/api/v1/jobs/<JOB_ID> | jq .
```

**Expected Output:**
```json
{
  "status": "failed",
  "progress": 50,
  "error": {
    "code": "DEST_RULE_FREQUENCY_CAP",
    "message": "Frequency cap reached (1/7d). Next eligible post at 2026-10-31T12:28:53+00:00.",
    "retryable": true,
    "details": {
      "reschedule_at": "2026-10-31T12:28:53+00:00"
    }
  }
}
```

---

### Step 5: Command Center Web UI
**Action:** Switch to browser at `http://localhost:8001/`.

1. **✍️ Studio Tab:**
   - Click **"Insert Sample Post"**.
   - Show right panel:
     - **Community-Tailored Output** (auto-appended discussion prompt & forum styling).
     - **Brand Safety & Ban Risk Meter** (`A+ | Extremely Safe (12% Risk)`).
2. **🔌 Connectors Tab:**
   - View all 9 registered connectors (6 Core + 3 Advanced).
   - Toggle any connector switch to demonstrate the runtime **Kill-Switch**.
3. **📊 Catalogue Tab:**
   - Show the 155 curated communities with audience scores and posting policies.

---

### Step 6: 1,000-Row Catalogue Import Benchmark
**Action:** Run import benchmark in terminal.

```bash
.venv/bin/python -c "
import asyncio
from src.engine.catalogue_importer import import_catalogue_csv
with open('data/synthetic_1000_destinations.csv', 'rb') as f:
    res = asyncio.run(import_catalogue_csv(f.read()))
    print(f'Imported {res[\"imported\"]} rows in {res[\"duration_seconds\"]}s with {len(res[\"errors\"])} errors')
"
```

**Expected Output:**
```text
Imported 980 rows in 0.78s with 20 errors
```

---

### Step 7: Official Excel Submission Workbook
**Action:** Switch to Excel showing `IncuBrix_Assessment_4_Distribution_Long_Tail_Destination_Network_Submission_Form.xlsx`.

- **Sheet `3_Levels`:** Show **Calculated Level: "Outstanding" (40/40 marks)**.
- **Sheet `4_Integration`:** Show **Integration Standard: 20/20 marks**.
- **Sheet `7_Declaration`:** Show **Signed Declaration**.

---

## ✅ Post-Recording Checklist

- [ ] Check video duration in player: **Between 7m 00s and 7m 45s** (strictly under 8m).
- [ ] Ensure video is continuous (unedited single take).
- [ ] Upload video to YouTube (Unlisted) or Google Drive (public view permissions).
- [ ] Paste video link into **Row 13** of Sheet `1_Your_Details` in `IncuBrix_Assessment_4_Distribution_Long_Tail_Destination_Network_Submission_Form.xlsx`.

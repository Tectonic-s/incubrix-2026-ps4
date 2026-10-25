# IncuBrix 2027 — PS4: Easy-to-Follow Demo Video Guide

> **Single Source of Truth for Recording Your Unedited 7-Minute Demo Video**  
> *Target Duration: 7m 00s to 7m 30s (Max allowed: 8m 00s)*  
> *Tone: Natural, relaxed, zero-jargon, confident software engineer.*

---

## 🛠️ 30-Second Pre-Recording Setup

1. **Terminal Open:** In `/Users/tectonic/Desktop/Incubrix/PS4` with `.venv` active (`source .venv/bin/activate`). Font size set to 16pt+ so text is easy to read on video.
2. **Browser Open:** Tab 1 open to `http://localhost:8001/` (Command Center UI).
3. **Excel Ready:** Have `IncuBrix_Assessment_4_Distribution_Long_Tail_Destination_Network_Submission_Form.xlsx` ready to show at the end.
4. **Recording Started:** Hit record on your screen recording tool (QuickTime or OBS). No editing needed!

---

## ⏱️ Step-by-Step Minute Guide

---

### Step 1 [0:00 – 1:00]: Introduction & The Problem We Solve
- **What to show on screen:** Browser showing the **Command Center UI** (`http://localhost:8001/`).
- **What to say aloud:**
  > *"Hi everyone, this is my submission demo for IncuBrix Problem Statement 4: Long-Tail Destination Network.*
  >
  > *The problem we're solving is simple: mainstream social platforms like Twitter or LinkedIn are easy to post to, but developers and high-value audiences actually hang out on niche forums like Discourse, Fediverse communities like Lemmy, blogging sites like Dev.to, and private Slack channels.*
  >
  > *The challenge is that every community has different rules, different APIs, and strict anti-spam policies. If you post too fast or sound like a marketer, they will ban your account.*
  >
  > *Our service acts as a safe, smart gateway: it checks rules before posting, tailors the text for each community, handles async jobs and safe retries, and connects to 9 different platforms. Here on port 8001, we have our live Command Center."*

---

### Step 2 [1:00 – 2:15]: Running All 42 Automated Tests
- **What to show on screen:** Switch to **Terminal**.
- **What command to run:**
  ```bash
  DATABASE_URL=sqlite:///./test_clean.db .venv/bin/pytest -v
  ```
- **What the output looks like:**
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
- **What to say aloud:**
  > *"Let's start by running our automated test suite.*
  >
  > *With one command, all 42 tests pass in under one second.*
  >
  > *This proves our 9 connectors work, our rules engine catches violations, our tailoring engine formats articles, and our recommendation engine hits 86.7% precision.*
  >
  > *We also test 7 tough edge cases like rate limits, expired tokens, oversized media, and platform schema drift."*

---

### Step 3 [2:15 – 3:45]: Publishing a Post & Proving Safe Retries (Idempotency)
- **What to show on screen:** Terminal.
- **Command 1 (Dispatch a new post):**
  ```bash
  curl -X POST http://localhost:8001/api/v1/publish \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: demo-video-key-001" \
    -d '{
      "destination_id": "discourse-dev-forum",
      "rendition": {
        "title": "Scaling Distributed Pipelines in 2027",
        "body": "A practical guide to worker queues and retry backoffs.",
        "tags": ["python", "architecture"]
      }
    }' | jq .
  ```
  - **Output on screen:** `HTTP 202 Accepted` with `"job_id": "job_...", "status": "queued"`.
  - **What to say aloud:**
    > *"Now let's publish a post. Because network calls take time, our API returns an immediate HTTP 202 Accepted with a job ID so the caller never hangs."*

- **Command 2 (Re-send the EXACT same command to prove idempotency):**
  - Hit `Up Arrow` in terminal and run the exact same `curl` again with the same `Idempotency-Key`.
  - **Output on screen:** Returns the exact same job ID immediately!
  - **What to say aloud:**
    > *"Now watch this: if my network drops and my client resends the exact same request with the same Idempotency Key, our server detects the duplicate and returns the existing job. It never creates a duplicate post or double-bills."*

- **Command 3 (Check the job status):**
  ```bash
  curl -s http://localhost:8001/api/v1/jobs/<PASTE_JOB_ID_HERE> | jq .
  ```
  - **Output on screen:** `"status": "succeeded", "progress": 100`, with `"live_url": "https://..."`.
  - **What to say aloud:**
    > *"When we poll the job ID, we see it finished with 100% progress and gives us the live confirmed post link and output manifest."*

---

### Step 4 [3:45 – 5:00]: Brand Safety in Action (Catching Rule Violations)
- **What to show on screen:** Terminal.
- **What command to run (Intentionally triggering a frequency cap rule):**
  ```bash
  curl -X POST http://localhost:8001/api/v1/publish \
    -H "Content-Type: application/json" \
    -d '{
      "destination_id": "discourse-freq-cap-test",
      "rendition": {
        "title": "Spamming another post too soon",
        "body": "This post violates community cooldown.",
        "tags": ["test"]
      }
    }' | jq .
  ```
  - Poll the returned `job_id`:
    ```bash
    curl -s http://localhost:8001/api/v1/jobs/<PASTE_JOB_ID_HERE> | jq .
    ```
- **What the output looks like:**
  ```json
  {
    "status": "failed",
    "error": {
      "code": "DEST_RULE_FREQUENCY_CAP",
      "message": "Frequency cap reached (1/7d). Next eligible post at 2026-10-31T18:00:00Z.",
      "retryable": true
    }
  }
  ```
- **What to say aloud:**
  > *"Now let's test brand safety. If you post to a developer forum too frequently, moderators will ban you.*
  >
  > *Here, I tried to post to a forum with a 7-day cooldown. Look at the output: our rules engine intercepted it before sending anything over the network.*
  >
  > *It returns an explicit error: DEST_RULE_FREQUENCY_CAP, and gives the exact date and time we are allowed to post again. The same system catches self-promotion links and missing AI disclosures."*

---

### Step 5 [5:00 – 6:15]: The Command Center UI & Live Content Tailoring
- **What to show on screen:** Switch back to **Browser** at `http://localhost:8001/`.
- **What to do on screen:**
  1. Click the **"✍️ Studio"** tab.
  2. Click the button **"Insert Sample Post"**.
  3. Point to the **Split-Screen** on the right:
     - Show the **"Community-Tailored Output"**: point out how the title became an open question (*"What are your thoughts on: ...?"*) and added a discussion prompt at the bottom.
     - Show the **"Brand Safety & Ban Risk Meter"**: point to the green circle showing `Risk: 12% | A+ (Extremely Safe)`.
  4. Click the **"🔌 Connectors"** tab:
     - Show the 9 connectors (Discourse, Lemmy, Dev.to, Ghost, Webhook, Assisted, Hashnode, Slack, MRSS).
     - Flip one of the toggle switches to demonstrate the runtime **Kill-Switch**.
- **What to say aloud:**
  > *"To make this intuitive, we built this interactive Command Center UI.*
  >
  > *In the Studio, as we write an article, our Tailoring Engine automatically rewrites it for the target community.*
  >
  > *For forums like Discourse, it turns our article into an engaging discussion starter instead of a broadcast link, and for blogs like Dev.to, it injects canonical SEO links.*
  >
  > *Notice our Ban Risk Meter: it analyzes marketing buzzwords and link density in real time, scoring this an A+.*
  >
  > *In the Connectors tab, we have all 9 connectors with live circuit breakers and instant kill-switches: with one click, I can disable any connector if a platform has downtime."*

---

### Step 6 [6:15 – 7:15]: High-Speed Catalogue Import Benchmark (1,000 Rows)
- **What to show on screen:** Switch to **Terminal**.
- **What command to run:**
  ```bash
  .venv/bin/python -c "
  import asyncio
  from src.engine.catalogue_importer import import_catalogue_csv
  with open('data/synthetic_1000_destinations.csv', 'rb') as f:
      res = asyncio.run(import_catalogue_csv(f.read()))
      print(f'Imported {res[\"imported\"]} rows in {res[\"duration_seconds\"]}s with {len(res[\"errors\"])} errors')
  "
  ```
- **What the output looks like:**
  ```text
  Imported 980 rows in 0.78s with 20 errors
  ```
- **What to say aloud:**
  > *"For large-scale operations, the brief required importing a CSV of 1,000 destinations in under 5 minutes.*
  >
  > *Our importer validated, normalized URLs, and deduplicated 1,000 rows in just 0.78 seconds—hundreds of times faster than the requirement.*
  >
  > *It also caught 20 malformed test rows with row-by-row error diagnostics."*

---

### Step 7 [7:15 – 7:45]: Official Excel Workbook & Wrap-Up
- **What to show on screen:** Switch to **Excel** (or preview) showing `IncuBrix_Assessment_4_Distribution_Long_Tail_Destination_Network_Submission_Form.xlsx`.
- **What to show in the workbook:**
  - Click on the `3_Levels` tab: show **Calculated Level: "Outstanding" (40/40 marks)**.
  - Click on the `4_Integration` tab: show **Integration Standard: 20/20 marks**.
  - Click on the `7_Declaration` tab: show **Signed Declaration**.
- **What to say aloud:**
  > *"To wrap up, here is our official submission form: IncuBrix_Assessment_4_Distribution_Long_Tail_Destination_Network_Submission_Form.xlsx.*
  >
  > *Every single yellow input cell, evidence link, and measurement is filled out.*
  >
  > *All 9 must-haves are verified, our calculated level is Outstanding with 40 out of 40 marks, and all 10 Integration Standards are met.*
  >
  > *Everything is committed in git, fully containerised, and ready for review. Thank you!"*

---

## ✅ Post-Recording Checklist

- [ ] Check video duration in player: **Between 7m 00s and 7m 45s** (under the 8-minute limit).
- [ ] Check audio: Voice is clear and audible over terminal keystrokes.
- [ ] No cuts or splices (continuous single-take).
- [ ] Upload to YouTube (Unlisted) or Google Drive (Share $\rightarrow$ "Anyone with link can view").
- [ ] Paste video link into Row 13 of Sheet `1_Your_Details` in your Excel submission workbook.

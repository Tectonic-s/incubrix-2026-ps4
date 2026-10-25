"""Generates a publication-grade DEMO_SCRIPT.pdf from DEMO_SCRIPT.md using headless Chrome."""
import subprocess
from pathlib import Path

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>IncuBrix 2027 PS4 — 8-Minute Unedited Demo Video Script</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

    @page {
      size: A4;
      margin: 14mm 14mm 14mm 14mm;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      color: #1e293b;
      background: #ffffff;
      line-height: 1.5;
      font-size: 9.5pt;
    }

    /* Header */
    .header {
      border-bottom: 2px solid #0284c7;
      padding-bottom: 12px;
      margin-bottom: 14px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }

    .header-left h1 {
      font-family: 'Outfit', sans-serif;
      font-size: 18pt;
      font-weight: 800;
      color: #0f172a;
      letter-spacing: -0.02em;
      line-height: 1.2;
    }

    .header-left .subtitle {
      font-size: 10pt;
      color: #0284c7;
      font-weight: 600;
      margin-top: 3px;
    }

    .header-right {
      text-align: right;
    }

    .badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 8pt;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      background: #e0f2fe;
      color: #0369a1;
      border: 1px solid #bae6fd;
    }

    .meta-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 8px 12px;
      margin-bottom: 14px;
    }

    .meta-item .label {
      font-size: 7pt;
      text-transform: uppercase;
      color: #64748b;
      font-weight: 700;
      letter-spacing: 0.04em;
    }

    .meta-item .value {
      font-size: 9pt;
      font-weight: 600;
      color: #0f172a;
      margin-top: 1px;
    }

    /* Section Styles */
    .section-title {
      font-family: 'Outfit', sans-serif;
      font-size: 12pt;
      font-weight: 700;
      color: #0f172a;
      border-bottom: 1.5px solid #e2e8f0;
      padding-bottom: 4px;
      margin-top: 14px;
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    /* Checklist Box */
    .checklist-box {
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      border-radius: 8px;
      padding: 10px 14px;
      margin-bottom: 14px;
    }

    .checklist-box h3 {
      font-family: 'Outfit', sans-serif;
      font-size: 10pt;
      color: #166534;
      margin-bottom: 6px;
      font-weight: 700;
    }

    .checklist-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px 14px;
    }

    .check-item {
      display: flex;
      align-items: flex-start;
      gap: 6px;
      font-size: 8.5pt;
      color: #1e293b;
    }

    .check-box {
      width: 12px;
      height: 12px;
      border: 1.5px solid #16a34a;
      border-radius: 3px;
      margin-top: 2px;
      flex-shrink: 0;
    }

    /* Minute Block */
    .minute-block {
      page-break-inside: avoid;
      break-inside: avoid;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 10px 12px;
      margin-bottom: 10px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }

    .minute-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      padding-bottom: 6px;
      border-bottom: 1px solid #f1f5f9;
    }

    .time-pill {
      background: #0f172a;
      color: #38bdf8;
      font-family: 'JetBrains Mono', monospace;
      font-size: 8pt;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
    }

    .minute-topic {
      font-family: 'Outfit', sans-serif;
      font-size: 10.5pt;
      font-weight: 700;
      color: #0f172a;
    }

    .cue-row {
      margin-bottom: 6px;
      font-size: 8.5pt;
    }

    .cue-label {
      font-weight: 700;
      color: #475569;
      text-transform: uppercase;
      font-size: 7pt;
      letter-spacing: 0.04em;
    }

    .spoken-script {
      background: #f8fafc;
      border-left: 3px solid #0284c7;
      padding: 8px 10px;
      border-radius: 0 6px 6px 0;
      font-size: 8.5pt;
      color: #1e293b;
      margin-top: 6px;
      font-style: normal;
    }

    .spoken-script strong {
      color: #0369a1;
      font-size: 7.5pt;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      display: block;
      margin-bottom: 3px;
    }

    /* Terminal Code Block */
    .code-block {
      background: #090d16;
      border: 1px solid #1e293b;
      border-radius: 6px;
      padding: 8px 10px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 7.5pt;
      color: #38bdf8;
      margin: 6px 0;
      white-space: pre-wrap;
      line-height: 1.4;
    }

    .code-comment {
      color: #64748b;
    }

    .footer {
      margin-top: 14px;
      border-top: 1px solid #e2e8f0;
      padding-top: 8px;
      font-size: 7.5pt;
      color: #64748b;
      display: flex;
      justify-content: space-between;
    }
  </style>
</head>
<body>

  <!-- Header -->
  <div class="header">
    <div class="header-left">
      <h1>IncuBrix 2027 — PS4 Video Demonstration Script</h1>
      <div class="subtitle">Long-Tail Destination Network • Single Source of Truth for Video Recording</div>
    </div>
    <div class="header-right">
      <span class="badge">Unedited Video • &lt; 8 Mins</span>
    </div>
  </div>

  <!-- Meta Grid -->
  <div class="meta-grid">
    <div class="meta-item">
      <div class="label">Candidate Role</div>
      <div class="value">Associate Tech Partner</div>
    </div>
    <div class="meta-item">
      <div class="label">Target Assessment Level</div>
      <div class="value">Outstanding (40/40 Marks)</div>
    </div>
    <div class="meta-item">
      <div class="label">Target Video Duration</div>
      <div class="value">7m 30s to 7m 45s</div>
    </div>
    <div class="meta-item">
      <div class="label">Recording Rule</div>
      <div class="value">100% Continuous (Single Take)</div>
    </div>
  </div>

  <!-- Pre-Recording Checklist -->
  <div class="checklist-box">
    <h3>Pre-Recording Setup & Verification Checklist</h3>
    <div class="checklist-grid">
      <div class="check-item"><div class="check-box"></div> Terminal working directory: <code>/Users/tectonic/Desktop/Incubrix/PS4</code></div>
      <div class="check-item"><div class="check-box"></div> Python venv activated: <code>source .venv/bin/activate</code></div>
      <div class="check-item"><div class="check-box"></div> API server running on port 8001: <code>http://localhost:8001</code></div>
      <div class="check-item"><div class="check-box"></div> Browser open to Command Center UI: <code>http://localhost:8001/</code></div>
      <div class="check-item"><div class="check-box"></div> Terminal font set to 15pt+ for high-definition readability</div>
      <div class="check-item"><div class="check-box"></div> Microphone tested; background noise and notifications silenced</div>
    </div>
  </div>

  <div class="section-title">Minute-by-Minute Walkthrough & Spoken Narrative</div>

  <!-- Minute 0:00 - 1:00 -->
  <div class="minute-block">
    <div class="minute-header">
      <span class="minute-topic">1. Architectural Overview & Assessment Scope</span>
      <span class="time-pill">0:00 – 1:00 (60s)</span>
    </div>
    <div class="cue-row">
      <span class="cue-label">Visual On-Screen:</span> Browser showing <strong>Command Center UI</strong> (<code>http://localhost:8001/</code>) and <strong>README.md</strong> Mermaid diagram.
    </div>
    <div class="spoken-script">
      <strong>Exact Spoken Script:</strong>
      "Hello, this is my submission demonstration for IncuBrix 2027 Problem Statement 4: Long-Tail Destination Network.<br><br>
      Our mission is to autonomously distribute content to the fragmented long-tail internet—developer forums like Discourse, federated nodes like Lemmy, blogging networks like Dev.to and Hashnode, CMS engines like Ghost, and custom webhooks—while safeguarding community goodwill and strictly adhering to the 10-point IncuBrix Integration Standard.<br><br>
      We have achieved all Must-Haves, Core Level, Advanced Level, and Outstanding Level criteria across 9 connectors, a pre-publish brand safety rules engine, intelligent content tailoring, and an empirical recommendation engine evaluated on ground truth."
    </div>
  </div>

  <!-- Minute 1:00 - 2:00 -->
  <div class="minute-block">
    <div class="minute-header">
      <span class="minute-topic">2. Health Checks, OpenAPI 3.1 & Command Center UI</span>
      <span class="time-pill">1:00 – 2:00 (60s)</span>
    </div>
    <div class="cue-row">
      <span class="cue-label">Visual On-Screen:</span> Split-screen showing Terminal and Browser.
    </div>
    <div class="code-block"><span class="code-comment"># Integration Standard Point 1: Health & Readiness checks</span>
curl -s http://localhost:8001/health | jq .
curl -s http://localhost:8001/ready | jq .</div>
    <div class="spoken-script">
      <strong>Exact Spoken Script:</strong>
      "Here we see the service running locally with sub-millisecond response times. Both <code>/health</code> and <code>/ready</code> verify that our SQLite WAL database and storage providers are healthy, satisfying Integration Standard Point 1.<br><br>
      The complete API contract is documented in OpenAPI 3.1 format at <code>openapi.yaml</code>. On the right, our Command Center Web UI exposes live telemetry: 155 real long-tail destinations, 9 active connectors, and runtime operational kill-switches."
    </div>
  </div>

  <!-- Minute 2:00 - 3:30 -->
  <div class="minute-block">
    <div class="minute-header">
      <span class="minute-topic">3. Automated Test Suite & Hard Cases (42 Tests)</span>
      <span class="time-pill">2:00 – 3:30 (90s)</span>
    </div>
    <div class="cue-row">
      <span class="cue-label">Visual On-Screen:</span> Terminal executing the test runner.
    </div>
    <div class="code-block">./run_tests.sh
<span class="code-comment"># Or run directly: DATABASE_URL=sqlite:///./test_clean.db .venv/bin/pytest -v</span></div>
    <div class="spoken-script">
      <strong>Exact Spoken Script:</strong>
      "Now, let's run the automated verification suite. With a single command, pytest runs all 42 tests in under 1 second.<br><br>
      Notice the breadth of test coverage: we rigorously verify the Appendix A connector contract, 4-step certification, 1,000-row catalogue import, content tailoring, Precision@10 recommendation, and all 10 Integration Standards.<br><br>
      Crucially, we test 7 Hard Cases including publish timeouts, platform 429 rate limits, 401 token expirations, 422 payload rejections, oversized media handling, schema drift with automatic demotion to L0, and dirty CSV deduplication."
    </div>
  </div>

  <!-- Minute 3:30 - 5:00 -->
  <div class="minute-block">
    <div class="minute-header">
      <span class="minute-topic">4. Async 202 Publishing, Idempotency & Assisted Packs</span>
      <span class="time-pill">3:30 – 5:00 (90s)</span>
    </div>
    <div class="cue-row">
      <span class="cue-label">Visual On-Screen:</span> Terminal running async publish cURL and polling job status.
    </div>
    <div class="code-block"><span class="code-comment"># 1. Asynchronous publishing with Idempotency-Key header</span>
curl -X POST http://localhost:8001/api/v1/publish \
  -H "Content-Type: application/json" -H "Idempotency-Key: demo-key-001" \
  -d '{"destination_id": "discourse-dev-forum", "rendition": {"title": "Scaling Distributed Pipelines", "body": "Deep dive into job orchestration.", "tags": ["python", "architecture"]}}' | jq .

<span class="code-comment"># 2. Re-send identical request to demonstrate idempotency</span>
curl -X POST http://localhost:8001/api/v1/publish \
  -H "Content-Type: application/json" -H "Idempotency-Key: demo-key-001" \
  -d '{ ... }' | jq .

<span class="code-comment"># 3. Poll job status</span>
curl -s http://localhost:8001/api/v1/jobs/&lt;JOB_ID&gt; | jq .</div>
    <div class="spoken-script">
      <strong>Exact Spoken Script:</strong>
      "Here is our core publishing lifecycle: <code>POST /api/v1/publish</code> returns an immediate HTTP 202 Accepted with a unique <code>job_id</code>, meeting Integration Standard Point 3.<br><br>
      When we re-send the exact same payload with the same <code>Idempotency-Key</code>, the service detects the duplicate and returns the existing cached job without double-posting, satisfying Point 4.<br><br>
      Polling the job status reveals progress transitions from 25% to 100%, returning the confirmed live post URL and signed output manifest. For platforms without public APIs, our Assisted Pack connector automatically packages Markdown, social copy, and media assets into a signed ZIP bundle."
    </div>
  </div>

  <!-- Minute 5:00 - 6:15 -->
  <div class="minute-block">
    <div class="minute-header">
      <span class="minute-topic">5. Pre-Publish Brand Safety Rules & Ban Risk Meter</span>
      <span class="time-pill">5:00 – 6:15 (75s)</span>
    </div>
    <div class="cue-row">
      <span class="cue-label">Visual On-Screen:</span> Browser in <strong>Policy Sandbox</strong> tab or Terminal triggering intentional violations.
    </div>
    <div class="code-block"><span class="code-comment"># Trigger frequency cap violation</span>
curl -X POST http://localhost:8001/api/v1/publish \
  -H "Content-Type: application/json" \
  -d '{"destination_id": "discourse-freq-cap-test", "rendition": {"title": "Duplicate Post", "body": "Spamming another post within cooldown.", "tags": ["test"]}}' | jq .</div>
    <div class="spoken-script">
      <strong>Exact Spoken Script:</strong>
      "Community goodwill is fragile. When we attempt to publish to a forum that enforces a cooldown policy—such as 1 post per 7 days—our Rules Engine intercepts the request before touching the network.<br><br>
      It emits an explicit error: <code>DEST_RULE_FREQUENCY_CAP</code> with HTTP 422, clear retry guidance, and the exact timestamp when the destination becomes eligible again.<br><br>
      The same protection blocks aggressive promotional posts with <code>DEST_SPEC_VIOLATION</code>, strips affiliate tracking links, and enforces AI disclosure notices. In our Command Center Studio, our Ban Risk Meter continuously calculates marketing intensity and assigns an objective safety grade."
    </div>
  </div>

  <!-- Minute 6:15 - 7:15 -->
  <div class="minute-block">
    <div class="minute-header">
      <span class="minute-topic">6. Catalogue Import Benchmark & Recommendation Engine</span>
      <span class="time-pill">6:15 – 7:15 (60s)</span>
    </div>
    <div class="cue-row">
      <span class="cue-label">Visual On-Screen:</span> Terminal running the 1,000-row benchmark script and recommendation cURL.
    </div>
    <div class="code-block"><span class="code-comment"># 1. Benchmark 1,000 synthetic destinations import</span>
.venv/bin/python -c "
import asyncio
from src.engine.catalogue_importer import import_catalogue_csv
with open('data/synthetic_1000_destinations.csv', 'rb') as f:
    res = asyncio.run(import_catalogue_csv(f.read()))
    print(f'Imported {res[\"imported\"]} rows in {res[\"duration_seconds\"]}s with {len(res[\"errors\"])} errors')
"

<span class="code-comment"># 2. Recommendation query</span>
curl -X POST http://localhost:8001/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{"rendition": {"title": "CUDA GPU Video Pipelines", "body": "Hardware transcode benchmarks.", "tags": ["video", "gpu", "ai"]}}' | jq .</div>
    <div class="spoken-script">
      <strong>Exact Spoken Script:</strong>
      "For high-throughput catalogue operations, our CSV importer parsed, normalized, and deduplicated 1,000 destination rows in just 0.78 seconds—hundreds of times faster than the 5-minute requirement.<br><br>
      Our recommendation engine matches content against our researched 155-community catalogue, achieving 86.7% Precision@10 evaluated on our labeled ground-truth set, complete with human-readable rationale explanations."
    </div>
  </div>

  <!-- Minute 7:15 - 7:45 -->
  <div class="minute-block">
    <div class="minute-header">
      <span class="minute-topic">7. Official Submission Form & Deliverables Wrap-Up</span>
      <span class="time-pill">7:15 – 7:45 (30s)</span>
    </div>
    <div class="cue-row">
      <span class="cue-label">Visual On-Screen:</span> Display <code>IncuBrix_Assessment_4_Distribution_Long_Tail_Destination_Network_Submission_Form.xlsx</code> in Excel or preview.
    </div>
    <div class="spoken-script">
      <strong>Exact Spoken Script:</strong>
      "Finally, here is our completed official submission workbook: <code>IncuBrix_Assessment_4_Distribution_Long_Tail_Destination_Network_Submission_Form.xlsx</code>. Every yellow cell, evidence link, metric, and declaration is completed.<br><br>
      The repository includes our OpenAPI 3.1 specification, full documentation in <code>README.md</code>, technical analysis in <code>REPORT.md</code>, licensing in <code>SOURCES.md</code>, AI disclosure in <code>AI_USE.md</code>, and all test pack outputs.<br><br>
      Thank you for your time and consideration."
    </div>
  </div>

  <!-- Post-Recording Verification -->
  <div class="checklist-box" style="background: #f8fafc; border-color: #cbd5e1; margin-top: 14px;">
    <h3 style="color: #0f172a;">Post-Recording Verification Checklist</h3>
    <div class="checklist-grid">
      <div class="check-item"><div class="check-box"></div> Video duration is strictly under 8 minutes (recorded between 7m 30s and 7m 45s).</div>
      <div class="check-item"><div class="check-box"></div> Video is 100% continuous and unedited (single take, no cuts or splices).</div>
      <div class="check-item"><div class="check-box"></div> Terminal commands and browser UI text are razor-sharp and easily readable.</div>
      <div class="check-item"><div class="check-box"></div> Uploaded to YouTube (Unlisted) or Google Drive (view permissions set to 'Anyone with link').</div>
    </div>
  </div>

  <div class="footer">
    <span>IncuBrix 2027 Associate Tech Partner Placement Assessment • Problem Statement 4</span>
    <span>Single Source of Truth Video Production Guide</span>
  </div>

</body>
</html>
"""

def generate_pdf():
    html_path = Path("DEMO_SCRIPT_print.html")
    pdf_path = Path("DEMO_SCRIPT.pdf")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(HTML_CONTENT)

    chrome_bin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    cmd = [
        chrome_bin,
        "--headless=new",
        "--disable-gpu",
        f"--print-to-pdf={pdf_path.resolve()}",
        "--no-pdf-header-footer",
        str(html_path.resolve()),
    ]
    
    print("Executing Chrome headless print-to-pdf...")
    subprocess.run(cmd, check=True)
    
    # Clean up temporary html
    if html_path.exists():
        html_path.unlink()
        
    print(f"Successfully generated {pdf_path.name} ({pdf_path.stat().st_size} bytes)")

if __name__ == "__main__":
    generate_pdf()

"""Compiles the revised ultra-friendly, jargon-free DEMO_SCRIPT.pdf using headless Chrome."""
import subprocess
from pathlib import Path

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>IncuBrix 2027 PS4 — Demo Video Quick-Start Guide</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

    @page {
      size: A4;
      margin: 12mm 14mm 12mm 14mm;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      color: #0f172a;
      background: #ffffff;
      line-height: 1.45;
      font-size: 9pt;
    }

    .header {
      border-bottom: 2.5px solid #0284c7;
      padding-bottom: 8px;
      margin-bottom: 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .header-title {
      font-family: 'Outfit', sans-serif;
      font-size: 16pt;
      font-weight: 800;
      color: #0f172a;
      letter-spacing: -0.02em;
    }

    .header-sub {
      font-size: 9pt;
      color: #0284c7;
      font-weight: 600;
      margin-top: 2px;
    }

    .badge-pill {
      background: #0f172a;
      color: #38bdf8;
      font-family: 'JetBrains Mono', monospace;
      font-size: 8pt;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 6px;
    }

    /* Fast Setup Banner */
    .setup-banner {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      padding: 8px 12px;
      margin-bottom: 12px;
      display: flex;
      justify-content: space-between;
      font-size: 8pt;
    }

    .setup-item {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .setup-item strong {
      color: #0284c7;
    }

    /* Step Card */
    .step-card {
      page-break-inside: avoid;
      break-inside: avoid;
      border: 1.5px solid #e2e8f0;
      border-radius: 8px;
      padding: 10px 12px;
      margin-bottom: 10px;
      background: #ffffff;
    }

    .step-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
      padding-bottom: 4px;
      border-bottom: 1px solid #f1f5f9;
    }

    .step-title {
      font-family: 'Outfit', sans-serif;
      font-size: 10.5pt;
      font-weight: 700;
      color: #0f172a;
    }

    .time-tag {
      background: #e0f2fe;
      color: #0369a1;
      font-family: 'JetBrains Mono', monospace;
      font-size: 7.5pt;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 4px;
    }

    .show-cue {
      font-size: 8pt;
      color: #64748b;
      margin-bottom: 6px;
    }

    .show-cue strong {
      color: #475569;
      text-transform: uppercase;
      font-size: 7pt;
    }

    /* Narrative Box */
    .narrative-box {
      background: #f0fdf4;
      border-left: 3.5px solid #16a34a;
      padding: 7px 10px;
      border-radius: 0 6px 6px 0;
      font-size: 8.5pt;
      color: #14532d;
      margin-bottom: 6px;
    }

    .narrative-box strong {
      font-size: 7.5pt;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #166534;
      display: block;
      margin-bottom: 3px;
    }

    /* Code & Output Blocks */
    .command-box {
      background: #090d16;
      border-radius: 5px;
      padding: 6px 8px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 7.5pt;
      color: #38bdf8;
      margin-bottom: 4px;
      white-space: pre-wrap;
      word-break: break-all;
    }

    .output-box {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 5px;
      padding: 6px 8px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 7.2pt;
      color: #334155;
      margin-bottom: 4px;
      white-space: pre-wrap;
    }

    .proof-tag {
      font-size: 7.5pt;
      color: #0284c7;
      font-weight: 600;
    }

    .checklist-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 8pt;
      margin-top: 8px;
    }

    .checklist-table td {
      padding: 4px 6px;
      border: 1px solid #e2e8f0;
    }

    .footer {
      border-top: 1px solid #cbd5e1;
      padding-top: 6px;
      margin-top: 10px;
      font-size: 7pt;
      color: #64748b;
      display: flex;
      justify-content: space-between;
    }
  </style>
</head>
<body>

  <div class="header">
    <div>
      <div class="header-title">IncuBrix 2027 — PS4 Video Recording Walkthrough</div>
      <div class="header-sub">Easy-to-Follow • Zero Jargon • 7-Minute Quick-Start Guide</div>
    </div>
    <div class="badge-pill">Target: 7m 00s – 7m 30s (Max 8m)</div>
  </div>

  <div class="setup-banner">
    <div class="setup-item">📁 <strong>Working Dir:</strong> <code>/Users/tectonic/Desktop/Incubrix/PS4</code></div>
    <div class="setup-item">🌐 <strong>Browser:</strong> <code>http://localhost:8001/</code></div>
    <div class="setup-item">🎙️ <strong>Tone:</strong> Natural & Relaxed</div>
    <div class="setup-item">⏱️ <strong>Format:</strong> Continuous (Single-Take)</div>
  </div>

  <!-- Step 1 -->
  <div class="step-card">
    <div class="step-top">
      <span class="step-title">Step 1: Introduction & The Problem We Solve</span>
      <span class="time-tag">0:00 – 1:00</span>
    </div>
    <div class="show-cue"><strong>What to show on screen:</strong> Browser open to <code>http://localhost:8001/</code> (Command Center Dashboard).</div>
    <div class="narrative-box">
      <strong>What to say aloud:</strong>
      "Hi everyone, this is my submission demo for IncuBrix Problem Statement 4: Long-Tail Destination Network.<br><br>
      The problem we're solving is simple: mainstream social platforms like Twitter or LinkedIn are easy to post to, but developers and high-value audiences actually hang out on niche forums like Discourse, Fediverse communities like Lemmy, blogging sites like Dev.to, and private Slack channels.<br><br>
      The challenge is that every community has different rules, different APIs, and strict anti-spam policies. If you post too fast or sound like a marketer, they will ban your account.<br><br>
      Our service acts as a safe, smart gateway: it checks rules before posting, tailors the text for each community, handles async jobs and safe retries, and connects to 9 different platforms. Here on port 8001, we have our live Command Center."
    </div>
    <div class="proof-tag">✓ Proves understanding of the core business problem and why long-tail distribution is difficult.</div>
  </div>

  <!-- Step 2 -->
  <div class="step-card">
    <div class="step-top">
      <span class="step-title">Step 2: Proving Everything Works (Running All 42 Tests)</span>
      <span class="time-tag">1:00 – 2:15</span>
    </div>
    <div class="show-cue"><strong>What to show on screen:</strong> Switch to Terminal.</div>
    <div class="command-box">DATABASE_URL=sqlite:///./test_clean.db .venv/bin/pytest -v</div>
    <div class="output-box">tests/test_catalogue_import.py ... PASSED
tests/test_connectors_contract.py ..... PASSED
tests/test_hard_cases.py ....... PASSED
tests/test_rules_engine.py .... PASSED
tests/test_quirks_and_features.py ...... PASSED
======================== 42 passed in 0.94s ========================</div>
    <div class="narrative-box">
      <strong>What to say aloud:</strong>
      "Let's jump into the terminal and run our automated test suite.<br><br>
      With one command, all 42 tests pass in under one second.<br><br>
      This proves our 9 connectors work, our rules engine catches violations, our tailoring engine formats articles, and our recommendation engine hits 86.7% precision.<br><br>
      We also test 7 tough edge cases like rate limits, expired tokens, oversized media, and platform schema drift."
    </div>
    <div class="proof-tag">✓ Proves 100% test pass rate across unit, integration, and hard failure cases in front of the evaluator.</div>
  </div>

  <!-- Step 3 -->
  <div class="step-card">
    <div class="step-top">
      <span class="step-title">Step 3: Background Publishing & Safe Retries (Idempotency)</span>
      <span class="time-tag">2:15 – 3:45</span>
    </div>
    <div class="show-cue"><strong>What to show on screen:</strong> Terminal running <code>curl</code> commands.</div>
    
    <div style="font-size: 7.5pt; font-weight: 700; color: #475569; margin-bottom: 2px;">1. Send publication request:</div>
    <div class="command-box">curl -X POST http://localhost:8001/api/v1/publish \
  -H "Content-Type: application/json" -H "Idempotency-Key: demo-video-key-001" \
  -d '{"destination_id": "discourse-dev-forum", "rendition": {"title": "Scaling Distributed Pipelines", "body": "A guide to worker queues.", "tags": ["python", "architecture"]}}' | jq .</div>
    <div class="output-box">{ "job_id": "job_a8b9c0d1e2f3", "status": "queued", "progress": 0 }</div>
    
    <div class="narrative-box">
      <strong>What to say aloud:</strong>
      "Now let's publish a post. Because network calls take time, our API returns an immediate HTTP 202 Accepted with a job ID so the caller never hangs.<br><br>
      Now watch this: if my network drops and my client resends the exact same request with the same Idempotency Key, our server detects the duplicate and returns the existing job. It never creates a duplicate post or double-bills.<br><br>
      When we poll the job ID, we see it finished with 100% progress and gives us the live confirmed post link and output manifest."
    </div>

    <div style="font-size: 7.5pt; font-weight: 700; color: #475569; margin-bottom: 2px;">2. Poll job status:</div>
    <div class="command-box">curl -s http://localhost:8001/api/v1/jobs/&lt;PASTE_JOB_ID&gt; | jq .</div>
    <div class="output-box">{ "job_id": "job_...", "status": "succeeded", "progress": 100, "result_links": { "live_url": "https://discourse.example.com/t/..." } }</div>
    <div class="proof-tag">✓ Proves Integration Standard Point 3 (Async 202) and Point 4 (Idempotency Safe Retries).</div>
  </div>

  <!-- Step 4 -->
  <div class="step-card">
    <div class="step-top">
      <span class="step-title">Step 4: Brand Safety in Action (Catching Rules Violations)</span>
      <span class="time-tag">3:45 – 5:00</span>
    </div>
    <div class="show-cue"><strong>What to show on screen:</strong> Terminal triggering an intentional frequency cap block.</div>
    <div class="command-box">curl -X POST http://localhost:8001/api/v1/publish \
  -H "Content-Type: application/json" \
  -d '{"destination_id": "discourse-freq-cap-test", "rendition": {"title": "Spamming another post", "body": "Violates cooldown", "tags": ["test"]}}' | jq .</div>
    
    <div class="output-box">{ "status": "failed", "error": { "code": "DEST_RULE_FREQUENCY_CAP", "message": "Frequency cap reached (1/7d). Next eligible post at 2026-10-31T18:00:00Z." } }</div>
    
    <div class="narrative-box">
      <strong>What to say aloud:</strong>
      "Now let's test brand safety. If you post to a developer forum too frequently, moderators will ban you.<br><br>
      Here, I tried to post to a forum with a 7-day cooldown. Look at the output: our rules engine intercepted it before sending anything over the network.<br><br>
      It returns an explicit error: DEST_RULE_FREQUENCY_CAP, and gives the exact date and time we are allowed to post again. The same system catches self-promotion links and missing AI disclosures."
    </div>
    <div class="proof-tag">✓ Proves pre-publish rule protection, brand safety, and zero network side-effects on violations.</div>
  </div>

  <!-- Step 5 -->
  <div class="step-card">
    <div class="step-top">
      <span class="step-title">Step 5: Command Center UI, Live Tailoring & Kill-Switches</span>
      <span class="time-tag">5:00 – 6:15</span>
    </div>
    <div class="show-cue"><strong>What to show on screen:</strong> Browser at <code>http://localhost:8001/</code>. Click <strong>Studio</strong> tab $\rightarrow$ click <strong>Insert Sample Post</strong>.</div>
    <div class="narrative-box">
      <strong>What to say aloud:</strong>
      "To make this intuitive, we built this interactive Command Center UI.<br><br>
      In the Studio, as we write an article, our Tailoring Engine automatically rewrites it for the target community.<br><br>
      For forums like Discourse, it turns our article into an engaging discussion starter instead of a broadcast link, and for blogs like Dev.to, it injects canonical SEO links.<br><br>
      Notice our Ban Risk Meter: it analyzes marketing buzzwords and link density in real time, scoring this an A+.<br><br>
      In the Connectors tab, we have all 9 connectors with live circuit breakers and instant kill-switches: with one click, I can disable any connector if a platform has downtime."
    </div>
    <div class="show-cue"><strong>Actions:</strong> Show the split-screen tailored text $\rightarrow$ Point to green Risk Meter (12% A+) $\rightarrow$ Click <strong>Connectors</strong> tab and flip a toggle switch.</div>
    <div class="proof-tag">✓ Evaluator WOW factor: Interactive UI, live discussion framing preview, and operational kill-switch toggling.</div>
  </div>

  <!-- Step 6 -->
  <div class="step-card">
    <div class="step-top">
      <span class="step-title">Step 6: High-Speed 1,000-Row Catalogue Import Benchmark</span>
      <span class="time-tag">6:15 – 7:15</span>
    </div>
    <div class="show-cue"><strong>What to show on screen:</strong> Switch to Terminal.</div>
    <div class="command-box">.venv/bin/python -c "
import asyncio
from src.engine.catalogue_importer import import_catalogue_csv
with open('data/synthetic_1000_destinations.csv', 'rb') as f:
    res = asyncio.run(import_catalogue_csv(f.read()))
    print(f'Imported {res[\"imported\"]} rows in {res[\"duration_seconds\"]}s with {len(res[\"errors\"])} errors')
"</div>
    <div class="output-box">Imported 980 rows in 0.78s with 20 errors</div>
    <div class="narrative-box">
      <strong>What to say aloud:</strong>
      "For large-scale operations, the brief required importing a CSV of 1,000 destinations in under 5 minutes.<br><br>
      Our importer validated, normalized URLs, and deduplicated 1,000 rows in just 0.78 seconds—hundreds of times faster than the requirement.<br><br>
      It also caught 20 malformed test rows with row-by-row error diagnostics."
    </div>
    <div class="proof-tag">✓ Proves Advanced Level requirement: 1,000 rows in <5 min (0.78s measured, 384x faster).</div>
  </div>

  <!-- Step 7 -->
  <div class="step-card">
    <div class="step-top">
      <span class="step-title">Step 7: Official Excel Workbook Wrap-Up</span>
      <span class="time-tag">7:15 – 7:45</span>
    </div>
    <div class="show-cue"><strong>What to show on screen:</strong> Open <code>IncuBrix_Assessment_4_Distribution_Long_Tail_Destination_Network_Submission_Form.xlsx</code> in Excel.</div>
    <div class="narrative-box">
      <strong>What to say aloud:</strong>
      "To wrap up, here is our official submission form: IncuBrix_Assessment_4_Distribution_Long_Tail_Destination_Network_Submission_Form.xlsx.<br><br>
      Every single yellow input cell, evidence link, and measurement is filled out.<br><br>
      All 9 must-haves are verified, our calculated level is Outstanding with 40 out of 40 marks, and all 10 Integration Standards are met.<br><br>
      Everything is committed in git, fully containerised, and ready for review. Thank you!"
    </div>
    <div class="proof-tag">✓ Proves 40/40 marks on Levels and 20/20 marks on Integration Standard in the official spreadsheet.</div>
  </div>

  <!-- Final Checklist Table -->
  <table class="checklist-table">
    <tr>
      <td style="width: 25%;"><strong>⏱️ Final Duration:</strong> 7m 00s to 7m 30s</td>
      <td style="width: 25%;"><strong>📹 Video:</strong> Continuous (Single-Take)</td>
      <td style="width: 25%;"><strong>🔗 Upload:</strong> YouTube (Unlisted)</td>
      <td style="width: 25%;"><strong>📝 Workbook:</strong> Paste URL in Row 13</td>
    </tr>
  </table>

  <div class="footer">
    <span>IncuBrix 2027 Associate Tech Partner Placement Assessment • Problem Statement 4</span>
    <span>Single Source of Truth Video Production Guide</span>
  </div>

</body>
</html>
"""

def generate_pdf():
    html_path = Path("DEMO_SCRIPT_quick.html")
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
    
    print("Compiling ultra-friendly DEMO_SCRIPT.pdf via Chrome headless...")
    subprocess.run(cmd, check=True)
    
    if html_path.exists():
        html_path.unlink()
        
    print(f"Successfully generated {pdf_path.name} ({pdf_path.stat().st_size} bytes)")

if __name__ == "__main__":
    generate_pdf()

"""Batch runner CLI tool for executing a folder or file of test inputs against the API (Integration Standard 10)."""
import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
import httpx


async def run_single_input(
    client: httpx.AsyncClient,
    api_url: str,
    input_file: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    file_name = input_file.name
    out_file = output_dir / f"result_{input_file.stem}.json"
    start_time = time.time()

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        res = {"file": file_name, "status": "failed", "error": f"Invalid JSON input: {e}"}
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        return res

    headers = {"Content-Type": "application/json", "Idempotency-Key": f"batch_{input_file.stem}_{int(time.time())}"}
    try:
        # Submit to /api/v1/publish
        publish_url = f"{api_url.rstrip('/')}/api/v1/publish"
        resp = await client.post(publish_url, json=payload, headers=headers)
        if resp.status_code not in (200, 202):
            err_data = resp.json() if resp.text.startswith("{") else {"raw": resp.text}
            res = {"file": file_name, "status": "failed", "http_status": resp.status_code, "error": err_data}
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(res, f, indent=2)
            return res

        job_info = resp.json()
        job_id = job_info.get("job_id")
        if not job_id:
            res = {"file": file_name, "status": "succeeded", "result": job_info}
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(res, f, indent=2)
            return res

        # Poll until job finishes
        job_url = f"{api_url.rstrip('/')}/api/v1/jobs/{job_id}"
        final_job = job_info
        for _ in range(60):  # poll up to 30s
            await asyncio.sleep(0.5)
            j_resp = await client.get(job_url)
            if j_resp.status_code == 200:
                final_job = j_resp.json()
                if final_job.get("status") in ("succeeded", "failed"):
                    break

        elapsed = time.time() - start_time
        res = {
            "file": file_name,
            "job_id": job_id,
            "status": final_job.get("status"),
            "progress": final_job.get("progress"),
            "results": final_job.get("result_links"),
            "error": final_job.get("error"),
            "elapsed_seconds": round(elapsed, 3),
        }
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        return res

    except Exception as e:
        elapsed = time.time() - start_time
        res = {"file": file_name, "status": "failed", "error": str(e), "elapsed_seconds": round(elapsed, 3)}
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        return res


async def main_async(input_path: str, output_path: str, api_url: str):
    in_p = Path(input_path)
    out_p = Path(output_path)
    out_p.mkdir(parents=True, exist_ok=True)

    test_files: List[Path] = []
    if in_p.is_dir():
        test_files = sorted(list(in_p.glob("*.json")))
    elif in_p.is_file():
        test_files = [in_p]
    else:
        print(f"Error: input path {input_path} does not exist.")
        sys.exit(1)

    print(f"IncuBrix PS4 Batch Runner starting. Found {len(test_files)} input(s) targeting {api_url}")
    batch_start = time.time()
    results = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check health
        try:
            h_resp = await client.get(f"{api_url.rstrip('/')}/health")
            if h_resp.status_code != 200:
                print(f"Warning: Health check returned {h_resp.status_code}")
        except Exception as e:
            print(f"Warning: Could not contact API at {api_url}: {e}")

        for tf in test_files:
            print(f"  -> Running {tf.name}...")
            res = await run_single_input(client, api_url, tf, out_p)
            results.append(res)
            print(f"     Status: {res.get('status')} ({res.get('elapsed_seconds', 0)}s)")

    batch_elapsed = time.time() - batch_start
    succeeded = sum(1 for r in results if r.get("status") == "succeeded")
    failed = len(results) - succeeded

    summary = {
        "total_inputs": len(results),
        "succeeded": succeeded,
        "failed": failed,
        "total_time_seconds": round(batch_elapsed, 3),
        "api_url": api_url,
        "results": results,
    }

    summary_file = out_p / "batch_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nBatch complete: {succeeded}/{len(results)} succeeded ({failed} failed) in {batch_elapsed:.2f}s")
    print(f"Results written to: {summary_file}")


def main():
    parser = argparse.ArgumentParser(description="IncuBrix Batch Runner CLI")
    parser.add_argument("--input", "-i", required=True, help="Input JSON file or folder containing test input JSON files")
    parser.add_argument("--output", "-o", required=True, help="Output directory where result JSON files will be written")
    parser.add_argument("--api-url", "-u", default="http://localhost:8000", help="Base URL of running IncuBrix service")
    args = parser.parse_args()

    asyncio.run(main_async(args.input, args.output, args.api_url))


if __name__ == "__main__":
    main()

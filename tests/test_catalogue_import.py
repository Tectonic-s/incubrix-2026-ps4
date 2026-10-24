"""Tests validating catalogue import, deduplication, row-by-row errors, and 1,000-row benchmark."""
import time
from pathlib import Path
import pytest
from src.engine.catalogue_importer import catalogue_importer


def test_import_1000_synthetic_destinations_benchmark():
    csv_path = Path("./data/synthetic_1000_destinations.csv")
    assert csv_path.exists()

    with open(csv_path, "r", encoding="utf-8") as f:
        csv_content = f.read()

    start = time.time()
    report = catalogue_importer.import_csv(csv_content)
    elapsed = time.time() - start

    assert report["total_rows"] == 1000
    assert report["imported_count"] >= 900
    assert report["duplicates_count"] >= 30
    assert report["errors_count"] >= 20
    assert len(report["error_report"]) > 0

    # Must complete in under 5 minutes (300 seconds) - typically runs in under 3 seconds!
    assert elapsed < 300.0
    print(f"\n1,000 rows imported in {elapsed:.3f} seconds! (Benchmark threshold: <300s)")


def test_import_real_catalogue_150():
    csv_path = Path("./data/real_catalogue_150.csv")
    assert csv_path.exists()

    with open(csv_path, "r", encoding="utf-8") as f:
        csv_content = f.read()

    report = catalogue_importer.import_csv(csv_content)
    assert report["total_rows"] >= 150
    assert report["errors_count"] == 0
    print(f"\nReal catalogue imported: {report['imported_count']} rows in {report['time_seconds']}s")


def test_url_normalisation_and_deduplication():
    norm1 = catalogue_importer.normalise_url("https://www.Example.COM/c/Tech/")
    norm2 = catalogue_importer.normalise_url("http://example.com:80/c/Tech")
    assert norm1.replace("https://", "") == norm2.replace("http://", "")

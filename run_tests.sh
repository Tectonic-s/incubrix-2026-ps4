#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "IncuBrix 2027 PS4 — Long-Tail Distribution Test Suite"
echo "Running Unit, Integration, Hard Cases & End-to-End Tests"
echo "=========================================================="

# Check virtual environment
if [ -d ".venv" ]; then
    PYTHON_BIN=".venv/bin/python"
    PYTEST_BIN=".venv/bin/pytest"
else
    PYTHON_BIN="python3"
    PYTEST_BIN="pytest"
fi

export SIMULATION_MODE=true
export DATABASE_URL="sqlite:///./incubrix_ps4.db"

echo "1. Executing Pytest Test Suite..."
$PYTEST_BIN -v

echo ""
echo "2. Executing CLI Batch Runner on Test Pack..."
$PYTHON_BIN -m src.cli.batch_runner --input test_pack/inputs --output test_pack/outputs --api-url http://localhost:8000

echo ""
echo "=========================================================="
echo "All IncuBrix PS4 Verification Checks Completed Successfully!"
echo "=========================================================="

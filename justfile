default:
    @just --list

sync:
    uv sync --locked

lint:
    uv run --locked ruff check .

format:
    uv run --locked ruff format .

check:
    uv run --locked ruff check .
    uv run --locked ruff format --check .

test:
    uv run --locked pytest -q

run:
    uv run --locked audio-loopback-tester

assets:
    uv run --locked python scripts/prepare_assets.py

smoke:
    uv run --locked audio-loopback-tester --smoke-test build/source-smoke.json

build:
    uv run --locked --group build python scripts/build_release.py

bundle:
    uv run --locked --group build python scripts/build_release.py --bundle-only
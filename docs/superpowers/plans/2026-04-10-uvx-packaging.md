# UVX Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert this project into a publishable Python package that can be built with `uv` and exposed through a console script for later `uv publish`.

**Architecture:** Move runtime code from loose `scripts/` modules into a proper `src/seoul_metro_realtime/` package, then expose a console entry point from `pyproject.toml`. Update tests to import the installed package shape instead of mutating `sys.path`, and verify both tests and package build succeed before any publish step.

**Tech Stack:** Python 3.12+, uv, hatchling, pytest, httpx, python-dotenv

---

### Task 1: Add failing package-layout coverage

**Files:**
- Create: `tests/test_package_layout.py`
- Test: `tests/test_package_layout.py`

- [ ] **Step 1: Write the failing test**

```python
from seoul_metro_realtime.get_arrivals import main
from seoul_metro_realtime.station_lookup import normalize_station_name


def test_package_modules_are_importable():
    assert callable(main)
    assert normalize_station_name("서울역") == "서울"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_package_layout.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'seoul_metro_realtime'`

### Task 2: Implement package structure and entry point

**Files:**
- Create: `src/seoul_metro_realtime/__init__.py`
- Create: `src/seoul_metro_realtime/get_arrivals.py`
- Create: `src/seoul_metro_realtime/station_lookup.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write minimal implementation**

Move code into `src/seoul_metro_realtime/`, update imports to package-qualified imports, and define:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project.scripts]
seoul-metro-realtime = "seoul_metro_realtime.get_arrivals:main"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_package_layout.py -v`
Expected: PASS

### Task 3: Update existing tests for installed-package imports

**Files:**
- Modify: `tests/test_arrival_formatting.py`
- Modify: `tests/test_station_lookup.py`

- [ ] **Step 1: Replace `sys.path` mutation imports**

Use direct imports from `seoul_metro_realtime.get_arrivals` and `seoul_metro_realtime.station_lookup`.

- [ ] **Step 2: Run focused tests**

Run: `uv run pytest tests/test_arrival_formatting.py tests/test_station_lookup.py -v`
Expected: PASS

### Task 4: Verify build readiness

**Files:**
- Modify: `pyproject.toml` if build metadata needs cleanup

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -v`
Expected: PASS

- [ ] **Step 2: Build publishable artifacts**

Run: `uv build --no-sources`
Expected: PASS and create `dist/*.whl` and `dist/*.tar.gz`

- [ ] **Step 3: Document publish command**

Run later with credentials: `uv publish`

#!/usr/bin/env python3
"""Validate a grader directory: manifest, syntax, and smoke run.

Usage:
    python scripts/validate_grader.py graders/my_grader
    python scripts/validate_grader.py graders/*          # validate all
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
TEST_INPUT = SCRIPT_DIR / "test_input.json"

REQUIRED_MANIFEST_FIELDS = {"name", "description", "language", "entrypoint"}
VALID_STATUSES = {"PASSED", "FAILED", "NOT_EVALUATED"}

LANGUAGE_EXTENSIONS = {
    "python": {".py"},
    "javascript": {".js"},
    "typescript": {".ts"},
}


def _fail(msg: str) -> None:
    print(f"  FAIL: {msg}", file=sys.stderr)


def _ok(msg: str) -> None:
    print(f"  OK:   {msg}")


def validate_manifest(grader_dir: Path) -> dict | None:
    """Check grader.yaml exists and has required fields. Returns parsed manifest or None."""
    manifest_path = grader_dir / "grader.yaml"
    if not manifest_path.exists():
        _fail(f"Missing grader.yaml in {grader_dir}")
        return None

    try:
        manifest = yaml.safe_load(manifest_path.read_text())
    except yaml.YAMLError as exc:
        _fail(f"Invalid YAML in {manifest_path}: {exc}")
        return None

    if not isinstance(manifest, dict):
        _fail(f"grader.yaml must be a YAML mapping, got {type(manifest).__name__}")
        return None

    missing = REQUIRED_MANIFEST_FIELDS - set(manifest.keys())
    if missing:
        _fail(f"grader.yaml missing required fields: {sorted(missing)}")
        return None

    entrypoint = manifest["entrypoint"]
    entry_path = grader_dir / entrypoint
    if not entry_path.exists():
        _fail(f"Entrypoint file not found: {entry_path}")
        return None

    dir_name = grader_dir.name
    if manifest["name"] != dir_name:
        _fail(
            f"Manifest name '{manifest['name']}' does not match "
            f"directory name '{dir_name}'"
        )
        return None

    _ok(f"Manifest valid ({manifest_path})")
    return manifest


def validate_syntax(grader_dir: Path, manifest: dict) -> bool:
    """Check syntax and basic structure of the grader source file."""
    language = manifest.get("language", "python")
    entrypoint = manifest["entrypoint"]
    entry_path = grader_dir / entrypoint

    if language == "python":
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(entry_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            _fail(f"Syntax error in {entry_path}:\n{result.stderr}")
            return False
        _ok(f"Python syntax valid ({entry_path})")

        source = entry_path.read_text()
        if "agentevals_grader_sdk" not in source:
            _fail(
                f"{entry_path} does not import agentevals_grader_sdk. "
                f"Graders must use the SDK or implement the stdin/stdout protocol."
            )
            return False
        if "@grader" not in source:
            _fail(f"{entry_path} does not use the @grader decorator")
            return False
        _ok("Imports and decorator present")

    elif language in ("javascript", "typescript"):
        ext = Path(entrypoint).suffix
        expected = LANGUAGE_EXTENSIONS.get(language, set())
        if ext not in expected:
            _fail(
                f"Entrypoint extension '{ext}' doesn't match "
                f"language '{language}' (expected {expected})"
            )
            return False
        _ok(f"Extension matches language ({entry_path})")

    return True


def validate_smoke_run(grader_dir: Path, manifest: dict) -> bool:
    """Run the grader with synthetic input and validate the output."""
    language = manifest.get("language", "python")
    entrypoint = manifest["entrypoint"]
    entry_path = grader_dir / entrypoint

    if language == "python":
        cmd = [sys.executable, str(entry_path)]
    elif language in ("javascript", "typescript"):
        cmd = ["node", str(entry_path)]
    else:
        _ok(f"Skipping smoke run for unsupported language: {language}")
        return True

    test_input = TEST_INPUT.read_text()

    result = subprocess.run(
        cmd,
        input=test_input,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        stderr_preview = result.stderr.strip()[:500]
        _fail(
            f"Grader exited with code {result.returncode}\n"
            f"  stderr: {stderr_preview}"
        )
        return False

    stdout = result.stdout.strip()
    if not stdout:
        stderr_preview = result.stderr.strip()[:500]
        _fail(
            f"Grader produced no output on stdout"
            + (f"\n  stderr: {stderr_preview}" if stderr_preview else "")
        )
        return False

    try:
        output = json.loads(stdout)
    except json.JSONDecodeError as exc:
        _fail(f"Grader stdout is not valid JSON: {exc}\n  stdout: {stdout[:200]}")
        return False

    # Validate score
    score = output.get("score")
    if score is None:
        _fail("Output missing required 'score' field")
        return False
    if not isinstance(score, (int, float)):
        _fail(f"'score' must be a number, got {type(score).__name__}: {score}")
        return False
    if score < 0.0 or score > 1.0:
        _fail(f"'score' must be in [0.0, 1.0], got {score}")
        return False

    # Validate status
    status = output.get("status")
    if status is not None and status not in VALID_STATUSES:
        _fail(
            f"'status' must be one of {sorted(VALID_STATUSES)} or null, "
            f"got '{status}'"
        )
        return False

    # Validate details type
    details = output.get("details")
    if details is not None and not isinstance(details, dict):
        _fail(
            f"'details' must be a dict or null, "
            f"got {type(details).__name__}: {details!r}"
        )
        return False

    # Validate per_invocation_scores type
    per_inv = output.get("per_invocation_scores")
    if per_inv is not None:
        if not isinstance(per_inv, list):
            _fail(
                f"'per_invocation_scores' must be a list, "
                f"got {type(per_inv).__name__}"
            )
            return False

    # Full Pydantic validation via the SDK if available
    try:
        from agentevals_grader_sdk import EvalResult
        EvalResult.model_validate(output)
        _ok("Output validates against EvalResult schema (Pydantic)")
    except ImportError:
        _ok("Output JSON structure valid (SDK not installed, skipped Pydantic check)")
    except Exception as exc:
        _fail(f"Output fails EvalResult validation: {exc}")
        return False

    _ok(f"Smoke run passed (score={score})")
    return True


def validate_grader(grader_dir: Path) -> bool:
    """Run all validations on a single grader directory."""
    print(f"\nValidating: {grader_dir}")
    print(f"{'─' * 50}")

    manifest = validate_manifest(grader_dir)
    if manifest is None:
        return False

    if not validate_syntax(grader_dir, manifest):
        return False

    if not validate_smoke_run(grader_dir, manifest):
        return False

    return True


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <grader_dir> [<grader_dir> ...]", file=sys.stderr)
        sys.exit(2)

    dirs = [Path(arg) for arg in sys.argv[1:]]
    results: dict[str, bool] = {}

    for d in dirs:
        if not d.is_dir():
            print(f"\nSkipping {d} (not a directory)", file=sys.stderr)
            continue
        if not (d / "grader.yaml").exists():
            print(f"\nSkipping {d} (no grader.yaml)", file=sys.stderr)
            continue
        results[str(d)] = validate_grader(d)

    print(f"\n{'=' * 50}")
    print("Summary:")
    all_passed = True
    for name, passed in results.items():
        icon = "PASS" if passed else "FAIL"
        print(f"  [{icon}] {name}")
        if not passed:
            all_passed = False

    if not results:
        print("  No graders found to validate.")
        sys.exit(2)

    print()
    if all_passed:
        print(f"All {len(results)} grader(s) passed.")
    else:
        failed = sum(1 for v in results.values() if not v)
        print(f"{failed} of {len(results)} grader(s) failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()

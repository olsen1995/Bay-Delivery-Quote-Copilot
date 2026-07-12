from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest
from fastapi.testclient import TestClient

from app import storage
from app.main import app


REPO_ROOT = Path(__file__).resolve().parents[1]
OPERATIONAL_DB_PATH = (REPO_ROOT / "app/data/bay_delivery.sqlite3").resolve()
PROBE_RESULT_ENV = "BAYDELIVERY_PYTEST_DB_PROBE_RESULT"
ABSENT = object()


def _run_probe(tmp_path: Path, database_path: object = ABSENT) -> tuple[subprocess.CompletedProcess[str], Path]:
    result_path = tmp_path / "probe-result.json"
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env[PROBE_RESULT_ENV] = str(result_path)
    if database_path is ABSENT:
        env.pop("BAYDELIVERY_DB_PATH", None)
    else:
        env["BAYDELIVERY_DB_PATH"] = str(database_path)

    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "-q",
            "-s",
            str(Path(__file__).resolve()),
            "-k",
            "test_subprocess_database_isolation_probe",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return result, result_path


def _read_probe_result(result: subprocess.CompletedProcess[str], result_path: Path) -> dict[str, object]:
    assert result.returncode == 0, result.stdout + result.stderr
    assert result_path.exists(), result.stdout + result.stderr
    return json.loads(result_path.read_text(encoding="utf-8"))


def test_subprocess_database_isolation_probe() -> None:
    result_path_value = os.environ.get(PROBE_RESULT_ENV)
    if result_path_value is None:
        selected_path = Path(os.environ["BAYDELIVERY_DB_PATH"]).resolve()
        assert selected_path != OPERATIONAL_DB_PATH
        assert REPO_ROOT not in selected_path.parents
        assert "app.main" in sys.modules
        return

    selected_env_value = os.environ["BAYDELIVERY_DB_PATH"]
    selected_path = Path(selected_env_value).resolve()
    with TestClient(app) as client:
        health_status = client.get("/health").status_code

    override_path = Path(result_path_value).parent / "per-test-override.sqlite3"
    initial_resolved_path = storage._resolve_db_path().resolve()
    os.environ["BAYDELIVERY_DB_PATH"] = str(override_path)

    payload = {
        "selected_path": str(selected_path),
        "selected_env_value": selected_env_value,
        "storage_db_path": str(storage.DB_PATH),
        "storage_default_db_path": str(storage.DEFAULT_DB_PATH),
        "initial_resolved_path": str(initial_resolved_path),
        "override_resolved_path": str(storage._resolve_db_path().resolve()),
        "override_path": str(override_path.resolve()),
        "app_main_imported": "app.main" in sys.modules,
        "health_status": health_status,
    }
    Path(result_path_value).write_text(json.dumps(payload), encoding="utf-8")


def test_absent_environment_creates_and_cleans_external_temp_database(tmp_path: Path) -> None:
    result, result_path = _run_probe(tmp_path)
    payload = _read_probe_result(result, result_path)

    selected_path = Path(str(payload["selected_path"]))
    generated_directory = selected_path.parent
    temp_root = Path(tempfile.gettempdir()).resolve()

    assert selected_path != OPERATIONAL_DB_PATH
    assert REPO_ROOT not in selected_path.parents
    assert generated_directory.parent == temp_root
    assert not generated_directory.exists()
    assert payload["app_main_imported"] is True
    assert payload["health_status"] == 200


def test_caller_provided_safe_database_path_is_preserved(tmp_path: Path) -> None:
    caller_directory = tmp_path / "caller-owned"
    caller_directory.mkdir()
    caller_path = caller_directory / "caller.sqlite3"

    result, result_path = _run_probe(tmp_path, caller_path)
    payload = _read_probe_result(result, result_path)

    assert payload["selected_path"] == str(caller_path.resolve())
    assert payload["selected_env_value"] == str(caller_path)
    assert payload["initial_resolved_path"] == str(caller_path.resolve())
    assert caller_directory.exists()
    assert caller_path.exists()


def test_storage_default_sentinel_preserves_safe_per_test_environment_overrides(tmp_path: Path) -> None:
    result, result_path = _run_probe(tmp_path)
    payload = _read_probe_result(result, result_path)

    assert payload["storage_db_path"] == payload["storage_default_db_path"]
    assert payload["initial_resolved_path"] == payload["selected_path"]
    assert payload["override_resolved_path"] == payload["override_path"]


@pytest.mark.parametrize("database_path", [str(OPERATIONAL_DB_PATH), ""])
def test_unsafe_database_configuration_is_rejected_before_application_import(
    tmp_path: Path,
    database_path: str,
) -> None:
    result, result_path = _run_probe(tmp_path, database_path)

    assert result.returncode != 0
    assert "pytest database isolation refused" in result.stderr.lower()
    assert not result_path.exists()

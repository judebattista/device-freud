"""Unit tests for the companion validator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from schemas.tools import validate as v


def _valid_doc() -> dict:
    return {
        "schema_version": "1.0.0",
        "device": {"manufacturer": "Acme", "model": "X1"},
        "interfaces": [{"id": "i0", "kind": "ethernet"}],
        "protocols": [{"id": "p0", "kind": "scpi", "runs_on": ["i0"]}],
        "commands": [{
            "id": "noop", "name": "n", "description": "n",
            "parameters": [], "output": {"kind": "none"},
            "binding": {"protocol_id": "p0", "protocol_kind": "scpi",
                        "command_template": "x", "is_query": False}
        }]
    }


def test_valid_doc_passes(tmp_path: Path) -> None:
    p = tmp_path / "doc.json"
    p.write_text(__import__("json").dumps(_valid_doc()))
    ok, errors = v.validate_document(p)
    assert ok, f"unexpected errors: {errors}"
    assert errors == []


def test_duplicate_interface_ids_rejected(tmp_path: Path) -> None:
    doc = _valid_doc()
    doc["interfaces"] = [
        {"id": "i0", "kind": "ethernet"},
        {"id": "i0", "kind": "usb"}
    ]
    p = tmp_path / "doc.json"
    p.write_text(__import__("json").dumps(doc))
    ok, errors = v.validate_document(p)
    assert not ok
    assert any("i0" in e and "interfaces" in e for e in errors)


def test_protocol_runs_on_unknown_interface_rejected(tmp_path: Path) -> None:
    doc = _valid_doc()
    doc["protocols"][0]["runs_on"] = ["ghost"]
    p = tmp_path / "doc.json"
    p.write_text(__import__("json").dumps(doc))
    ok, errors = v.validate_document(p)
    assert not ok
    assert any("ghost" in e for e in errors)


def test_binding_unknown_protocol_id_rejected(tmp_path: Path) -> None:
    doc = _valid_doc()
    doc["commands"][0]["binding"]["protocol_id"] = "no_such_protocol"
    p = tmp_path / "doc.json"
    p.write_text(__import__("json").dumps(doc))
    ok, errors = v.validate_document(p)
    assert not ok
    assert any("no_such_protocol" in e for e in errors)


def test_binding_protocol_kind_mismatch_rejected(tmp_path: Path) -> None:
    doc = _valid_doc()
    # Add a Modbus protocol entry, but keep the command binding pointing at SCPI fields.
    # Then change the binding's protocol_id to point at the modbus protocol while leaving
    # protocol_kind as "scpi" - this mismatch is what check_protocol_refs detects.
    doc["protocols"].append({"id": "mb", "kind": "modbus_tcp", "runs_on": ["i0"]})
    # Binding still says protocol_kind: scpi but now points at the modbus protocol_id.
    doc["commands"][0]["binding"]["protocol_id"] = "mb"
    # The schema oneOf will match SCPI binding shape OK (protocol_kind: scpi),
    # but check_protocol_refs notices that protocols[mb].kind="modbus_tcp" != "scpi".
    p = tmp_path / "doc.json"
    p.write_text(__import__("json").dumps(doc))
    ok, errors = v.validate_document(p)
    assert not ok
    assert any("protocol_kind" in e and "scpi" in e and "modbus_tcp" in e for e in errors)


def test_template_references_unknown_param_rejected(tmp_path: Path) -> None:
    doc = _valid_doc()
    doc["commands"][0]["parameters"] = [
        {"name": "channel", "description": "ch", "type": "integer"}
    ]
    doc["commands"][0]["binding"]["command_template"] = ":MEAS:VOLT? (@{missing})"
    p = tmp_path / "doc.json"
    p.write_text(__import__("json").dumps(doc))
    ok, errors = v.validate_document(p)
    assert not ok
    assert any("missing" in e for e in errors)


def test_scpi_response_pattern_missing_value_group_rejected(tmp_path: Path) -> None:
    doc = _valid_doc()
    doc["commands"][0]["binding"] = {
        "protocol_id": "p0", "protocol_kind": "scpi",
        "command_template": ":X?", "is_query": True,
        "response_pattern": "(?P<other>.+)"
    }
    doc["commands"][0]["output"] = {"kind": "scalar", "type": "string"}
    p = tmp_path / "doc.json"
    p.write_text(__import__("json").dumps(doc))
    ok, errors = v.validate_document(p)
    assert not ok
    assert any("value" in e and "missing" in e.lower() for e in errors)


def test_scpi_response_pattern_record_fields_match_groups(tmp_path: Path) -> None:
    doc = _valid_doc()
    doc["commands"][0]["binding"] = {
        "protocol_id": "p0", "protocol_kind": "scpi",
        "command_template": ":X?", "is_query": True,
        "response_pattern": "(?P<voltage>[-+0-9.eE]+),(?P<current>[-+0-9.eE]+)"
    }
    doc["commands"][0]["output"] = {
        "kind": "record",
        "fields": [
            {"name": "voltage", "description": "V", "type": "number"},
            {"name": "current", "description": "A", "type": "number"}
        ]
    }
    p = tmp_path / "doc.json"
    p.write_text(__import__("json").dumps(doc))
    ok, errors = v.validate_document(p)
    assert ok, f"unexpected errors: {errors}"


def test_cli_accepts_all_positive_examples(examples_dir: Path) -> None:
    for f in sorted(examples_dir.glob("example-*.json")):
        result = subprocess.run(
            [sys.executable, "-m", "schemas.tools.validate", str(f)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"{f.name} failed:\n{result.stderr}"


def test_cli_rejects_all_invalid_fixtures(invalid_dir: Path) -> None:
    for f in sorted(invalid_dir.glob("*.json")):
        result = subprocess.run(
            [sys.executable, "-m", "schemas.tools.validate", str(f)],
            capture_output=True, text=True,
        )
        assert result.returncode == 1, f"{f.name} unexpectedly passed"
        assert "FAIL" in result.stderr

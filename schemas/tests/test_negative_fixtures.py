"""Negative fixtures: documents that must be rejected by the schema."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest


def _validate(schema: dict, doc: dict) -> list:
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(doc))
    # Collect context errors (nested errors from oneOf, allOf, etc.)
    result = []
    def collect(errs):
        for e in errs:
            result.append(e)
            if e.context:
                collect(e.context)
    collect(errors)
    return result


def _minimal() -> dict:
    return {
        "schema_version": "1.0.0",
        "device": {"manufacturer": "Acme", "model": "X1"},
        "interfaces": [{"id": "i0", "kind": "ethernet"}],
        "protocols": [{"id": "p0", "kind": "scpi", "runs_on": ["i0"]}],
        "commands": [{
            "id": "n", "name": "n", "description": "n",
            "parameters": [], "output": {"kind": "none"},
            "binding": {"protocol_id": "p0", "protocol_kind": "scpi",
                        "command_template": "x", "is_query": False}
        }]
    }


def test_empty_object_rejected(schema: dict) -> None:
    errors = _validate(schema, {})
    assert errors, "empty document must be rejected"


def test_missing_schema_version_rejected(schema: dict) -> None:
    doc = {"device": {}, "interfaces": [], "protocols": [], "commands": []}
    errors = _validate(schema, doc)
    assert any("schema_version" in str(e.message) or "schema_version" in str(e.path) for e in errors)


def test_device_missing_manufacturer_rejected(schema: dict) -> None:
    doc = {
        "schema_version": "1.0.0",
        "device": {"model": "X1"},
        "interfaces": [{"id": "i0", "kind": "ethernet"}],
        "protocols": [{"id": "p0", "kind": "scpi", "runs_on": ["i0"]}],
        "commands": [{
            "id": "n", "name": "n", "description": "n",
            "parameters": [], "output": {"kind": "none"},
            "binding": {"protocol_id": "p0", "protocol_kind": "scpi",
                        "command_template": "x", "is_query": False}
        }]
    }
    errors = _validate(schema, doc)
    assert any("manufacturer" in str(e.path) or "manufacturer" in str(e.message) for e in errors)


def test_device_extra_field_rejected(schema: dict) -> None:
    doc = {
        "schema_version": "1.0.0",
        "device": {"manufacturer": "Acme", "model": "X1", "unknown_field": "x"},
        "interfaces": [{"id": "i0", "kind": "ethernet"}],
        "protocols": [{"id": "p0", "kind": "scpi", "runs_on": ["i0"]}],
        "commands": [{
            "id": "n", "name": "n", "description": "n",
            "parameters": [], "output": {"kind": "none"},
            "binding": {"protocol_id": "p0", "protocol_kind": "scpi",
                        "command_template": "x", "is_query": False}
        }]
    }
    errors = _validate(schema, doc)
    assert any("unknown_field" in str(e.message) for e in errors)


def test_interface_unknown_kind_rejected(schema: dict) -> None:
    doc = {
        "schema_version": "1.0.0",
        "device": {"manufacturer": "Acme", "model": "X1"},
        "interfaces": [{"id": "i0", "kind": "telepathy"}],
        "protocols": [{"id": "p0", "kind": "scpi", "runs_on": ["i0"]}],
        "commands": [{
            "id": "n", "name": "n", "description": "n",
            "parameters": [], "output": {"kind": "none"},
            "binding": {"protocol_id": "p0", "protocol_kind": "scpi",
                        "command_template": "x", "is_query": False}
        }]
    }
    errors = _validate(schema, doc)
    assert any("kind" in str(e.path) for e in errors)


def test_interface_missing_id_rejected(schema: dict) -> None:
    doc = {
        "schema_version": "1.0.0",
        "device": {"manufacturer": "Acme", "model": "X1"},
        "interfaces": [{"kind": "ethernet"}],
        "protocols": [{"id": "p0", "kind": "scpi", "runs_on": ["i0"]}],
        "commands": [{
            "id": "n", "name": "n", "description": "n",
            "parameters": [], "output": {"kind": "none"},
            "binding": {"protocol_id": "p0", "protocol_kind": "scpi",
                        "command_template": "x", "is_query": False}
        }]
    }
    errors = _validate(schema, doc)
    assert any("id" in str(e.path) or "id" in str(e.message) for e in errors)


def test_protocol_empty_runs_on_rejected(schema: dict) -> None:
    doc = {
        "schema_version": "1.0.0",
        "device": {"manufacturer": "Acme", "model": "X1"},
        "interfaces": [{"id": "i0", "kind": "ethernet"}],
        "protocols": [{"id": "p0", "kind": "scpi", "runs_on": []}],
        "commands": [{
            "id": "n", "name": "n", "description": "n",
            "parameters": [], "output": {"kind": "none"},
            "binding": {"protocol_id": "p0", "protocol_kind": "scpi",
                        "command_template": "x", "is_query": False}
        }]
    }
    errors = _validate(schema, doc)
    assert any("runs_on" in str(e.path) or "minItems" in str(e.message) for e in errors)


def test_protocol_unknown_kind_rejected(schema: dict) -> None:
    doc = {
        "schema_version": "1.0.0",
        "device": {"manufacturer": "Acme", "model": "X1"},
        "interfaces": [{"id": "i0", "kind": "ethernet"}],
        "protocols": [{"id": "p0", "kind": "carrier_pigeon", "runs_on": ["i0"]}],
        "commands": [{
            "id": "n", "name": "n", "description": "n",
            "parameters": [], "output": {"kind": "none"},
            "binding": {"protocol_id": "p0", "protocol_kind": "carrier_pigeon",
                        "command_template": "x", "is_query": False}
        }]
    }
    errors = _validate(schema, doc)
    assert any("kind" in str(e.path) for e in errors)


def test_command_missing_description_rejected(schema: dict) -> None:
    doc = _minimal()
    doc["commands"] = [{
        "id": "x", "name": "x",
        "parameters": [], "output": {"kind": "none"},
        "binding": {"protocol_id": "p0", "protocol_kind": "scpi",
                    "command_template": "x", "is_query": False}
    }]
    errors = _validate(schema, doc)
    assert any("description" in str(e.message) for e in errors)


def test_command_unknown_category_rejected(schema: dict) -> None:
    doc = _minimal()
    doc["commands"][0]["category"] = "vibes"
    errors = _validate(schema, doc)
    assert any("category" in str(e.path) for e in errors)


def test_parameter_allowed_values_and_range_mutually_exclusive(schema: dict) -> None:
    doc = _minimal()
    doc["commands"][0]["parameters"] = [{
        "name": "x", "description": "x", "type": "integer",
        "allowed_values": [1, 2], "range": {"min": 0, "max": 10}
    }]
    errors = _validate(schema, doc)
    assert errors, "param with both allowed_values and range must be rejected"


def test_parameter_unknown_wire_type_rejected(schema: dict) -> None:
    doc = _minimal()
    doc["commands"][0]["parameters"] = [{
        "name": "x", "description": "x", "type": "integer", "wire_type": "uint13"
    }]
    errors = _validate(schema, doc)
    assert any("wire_type" in str(e.path) or "uint13" in str(e.message) for e in errors)


def test_output_record_missing_fields_rejected(schema: dict) -> None:
    doc = _minimal()
    doc["commands"][0]["output"] = {"kind": "record"}
    errors = _validate(schema, doc)
    assert errors, "record output without fields must be rejected"


def test_output_unknown_kind_rejected(schema: dict) -> None:
    doc = _minimal()
    doc["commands"][0]["output"] = {"kind": "telepathic"}
    errors = _validate(schema, doc)
    assert any("kind" in str(e.path) for e in errors)


def test_error_missing_code_rejected(schema: dict) -> None:
    doc = _minimal()
    doc["commands"][0]["errors"] = [{"description": "Bad."}]
    errors = _validate(schema, doc)
    assert any("code" in str(e.message) for e in errors)


def test_binding_unknown_protocol_kind_rejected(schema: dict) -> None:
    doc = _minimal()
    doc["commands"][0]["binding"]["protocol_kind"] = "morse_code"
    errors = _validate(schema, doc)
    assert errors, "unknown protocol_kind must be rejected by oneOf"


def test_binding_scpi_query_without_response_pattern_rejected(schema: dict) -> None:
    doc = _minimal()
    doc["commands"][0]["binding"] = {
        "protocol_id": "p0", "protocol_kind": "scpi",
        "command_template": "?", "is_query": True
    }
    errors = _validate(schema, doc)
    assert errors, "is_query=true without response_pattern must be rejected"


def test_binding_modbus_address_and_template_both_rejected(schema: dict) -> None:
    doc = _minimal()
    doc["protocols"][0] = {"id": "p0", "kind": "modbus_tcp", "runs_on": ["i0"]}
    doc["commands"][0]["binding"] = {
        "protocol_id": "p0", "protocol_kind": "modbus_tcp",
        "function_code": 3,
        "address": 40001, "address_template": "{x}",
        "byte_order": "ABCD"
    }
    errors = _validate(schema, doc)
    assert errors, "address and address_template are mutually exclusive"


def test_binding_modbus_missing_address_rejected(schema: dict) -> None:
    doc = _minimal()
    doc["protocols"][0] = {"id": "p0", "kind": "modbus_tcp", "runs_on": ["i0"]}
    doc["commands"][0]["binding"] = {
        "protocol_id": "p0", "protocol_kind": "modbus_tcp",
        "function_code": 3, "byte_order": "ABCD"
    }
    errors = _validate(schema, doc)
    assert errors, "modbus binding without address or address_template must be rejected"


def test_binding_http_rest_missing_method_rejected(schema: dict) -> None:
    doc = _minimal()
    doc["protocols"][0] = {"id": "api", "kind": "http_rest", "runs_on": ["i0"]}
    doc["commands"][0]["binding"] = {
        "protocol_id": "api", "protocol_kind": "http_rest",
        "path_template": "/x"
    }
    errors = _validate(schema, doc)
    assert errors, "http_rest binding without method must be rejected"


def test_binding_mqtt_qos_out_of_range_rejected(schema: dict) -> None:
    doc = _minimal()
    doc["protocols"][0] = {"id": "iot", "kind": "mqtt", "runs_on": ["i0"]}
    doc["commands"][0]["binding"] = {
        "protocol_id": "iot", "protocol_kind": "mqtt",
        "publish_topic_template": "x",
        "payload_template": {"shape": "json", "template": {}},
        "qos": 9
    }
    errors = _validate(schema, doc)
    assert errors, "mqtt binding with qos=9 must be rejected"


def test_binding_raw_serial_unknown_framing_rejected(schema: dict) -> None:
    doc = _minimal()
    doc["interfaces"][0] = {"id": "com1", "kind": "rs232"}
    doc["protocols"][0] = {"id": "p0", "kind": "raw_serial", "runs_on": ["com1"]}
    doc["commands"][0]["binding"] = {
        "protocol_id": "p0", "protocol_kind": "raw_serial",
        "framing": "telepathy",
        "request_frame": {"encoding": "hex", "value": "DEADBEEF"}
    }
    errors = _validate(schema, doc)
    assert any("framing" in str(e.path) for e in errors)


def test_binding_canopen_missing_cob_id_rejected(schema: dict) -> None:
    doc = _minimal()
    doc["interfaces"][0] = {"id": "can0", "kind": "can"}
    doc["protocols"][0] = {"id": "p0", "kind": "canopen", "runs_on": ["can0"]}
    doc["commands"][0]["binding"] = {
        "protocol_id": "p0", "protocol_kind": "canopen",
        "framing": "fixed_length",
        "request_frame": {"encoding": "hex", "value": "00"}
    }
    errors = _validate(schema, doc)
    assert errors, "canopen binding without cob_id must be rejected"


def test_binding_i2c_register_bad_device_address_rejected(schema: dict) -> None:
    doc = _minimal()
    doc["interfaces"][0] = {"id": "i2c0", "kind": "i2c"}
    doc["protocols"][0] = {"id": "p0", "kind": "i2c_register", "runs_on": ["i2c0"]}
    doc["commands"][0]["binding"] = {
        "protocol_id": "p0", "protocol_kind": "i2c_register",
        "device_address": 999,
        "register_address": 0, "access": "read", "byte_count": 1,
        "framing": "none",
        "request_frame": {"encoding": "hex", "value": "00"}
    }
    errors = _validate(schema, doc)
    assert any("device_address" in str(e.path) or "127" in str(e.message) for e in errors)


def test_binding_snmp_set_without_value_type_rejected(schema: dict) -> None:
    doc = _minimal()
    doc["protocols"][0] = {"id": "p0", "kind": "snmp", "runs_on": ["i0"]}
    doc["commands"][0]["binding"] = {
        "protocol_id": "p0", "protocol_kind": "snmp",
        "operation": "set", "oid_template": "1.3.6.1.2.1.1.5.0"
    }
    errors = _validate(schema, doc)
    assert errors, "snmp set without value_type must be rejected"


def test_binding_file_transfer_unknown_mechanism_rejected(schema: dict) -> None:
    doc = _minimal()
    doc["protocols"][0] = {"id": "ft", "kind": "file_transfer", "runs_on": ["i0"]}
    doc["commands"][0]["binding"] = {
        "protocol_id": "ft", "protocol_kind": "file_transfer",
        "mechanism": "carrier_pigeon", "direction": "download",
        "remote_path_template": "/x"
    }
    errors = _validate(schema, doc)
    assert any("mechanism" in str(e.path) for e in errors)


@pytest.mark.parametrize("filename", [
    "typo-field.json",
    "missing-required.json",
    "mismatched-kind.json",
    "bad-protocol-id.json",
])
def test_invalid_fixture_rejected(filename: str, invalid_dir: Path) -> None:
    from schemas.tools import validate as v
    ok, errors = v.validate_document(invalid_dir / filename)
    assert not ok, f"{filename} unexpectedly passed"
    assert errors, f"{filename} produced no error messages"

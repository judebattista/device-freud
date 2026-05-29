"""Positive fixtures: documents that must be accepted by the schema."""

from __future__ import annotations

import json
import jsonschema
from pathlib import Path


def _validate(schema: dict, doc: dict) -> list:
    validator = jsonschema.Draft202012Validator(schema)
    return list(validator.iter_errors(doc))


def _skeleton() -> dict:
    """Smallest document that has the right top-level shape; sub-schemas
    are filled in as the schema grows."""
    return {
        "schema_version": "1.0.0",
        "device": {"manufacturer": "Acme", "model": "X1"},
        "interfaces": [{"id": "i0", "kind": "ethernet"}],
        "protocols": [{"id": "p0", "kind": "scpi", "runs_on": ["i0"]}],
        "commands": [{
            "id": "noop",
            "name": "No-op",
            "description": "Does nothing.",
            "parameters": [],
            "output": {"kind": "none"},
            "binding": {
                "protocol_id": "p0",
                "protocol_kind": "scpi",
                "command_template": "*IDN?",
                "is_query": True,
                "response_pattern": "(?P<value>.+)"
            }
        }]
    }


def test_skeleton_valid(schema: dict) -> None:
    errors = _validate(schema, _skeleton())
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_interface_with_physical_block_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["interfaces"] = [{
        "id": "lan0",
        "kind": "ethernet",
        "connector": "RJ-45",
        "physical": {"link_speed_mbps": [10, 100, 1000]},
        "notes": "Front-panel network port.",
        "extensions": {"acme.poe": True}
    }]
    doc["protocols"][0]["runs_on"] = ["lan0"]
    doc["commands"][0]["binding"]["protocol_id"] = "p0"
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_protocol_with_full_metadata_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["protocols"] = [{
        "id": "modbus_lan",
        "kind": "modbus_tcp",
        "runs_on": ["i0"],
        "version": "1.1",
        "defaults": {"unit_id": 1, "timeout_ms": 1000},
        "connection": {"host_template": "{ip_address}", "port": 502},
        "extensions": {"vendor.foo": "bar"}
    }]
    doc["commands"][0]["binding"] = {
        "protocol_id": "modbus_lan",
        "protocol_kind": "modbus_tcp",
        "function_code": 3,
        "address": 40001,
        "quantity": 1,
        "byte_order": "ABCD"
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_command_with_all_optional_fields_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["commands"] = [{
        "id": "measure_voltage",
        "name": "Measure DC Voltage",
        "description": "Reads DC voltage from a channel.",
        "category": "measurement",
        "parameters": [],
        "output": {"kind": "scalar", "type": "number"},
        "binding": {
            "protocol_id": "p0",
            "protocol_kind": "scpi",
            "command_template": ":MEAS:VOLT:DC?",
            "is_query": True,
            "response_pattern": "(?P<value>[-+0-9.eE]+)"
        },
        "preconditions": ["channel must be enabled"],
        "side_effects":  ["resets the integration timer"],
        "errors": [],
        "examples": [],
        "extensions": {"tool.x": 1}
    }]
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_parameter_full_shape_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["commands"][0]["parameters"] = [{
        "name": "channel",
        "description": "Input channel index.",
        "type": "integer",
        "wire_type": "uint8",
        "units": None,
        "allowed_values": [1, 2, 3, 4],
        "default": 1,
        "required": True,
        "example": 2
    }]
    doc["commands"][0]["binding"]["command_template"] = ":MEAS:VOLT? (@{channel})"
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_parameter_range_only_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["commands"][0]["parameters"] = [{
        "name": "delay",
        "description": "Delay before measurement.",
        "type": "number",
        "wire_type": "float32",
        "units": "s",
        "range": {"min": 0.0, "max": 60.0, "step": 0.001},
        "default": 0.0
    }]
    doc["commands"][0]["binding"]["command_template"] = ":TRIG:DEL {delay}"
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_output_scalar_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["commands"][0]["output"] = {
        "kind": "scalar", "type": "number", "wire_type": "float32",
        "units": "V", "description": "Voltage in volts.", "example": 4.998
    }
    doc["commands"][0]["binding"]["response_pattern"] = "(?P<value>.+)"
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_output_record_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["commands"][0]["output"] = {
        "kind": "record",
        "fields": [
            {"name": "voltage", "description": "V", "type": "number", "wire_type": "float32", "units": "V"},
            {"name": "current", "description": "A", "type": "number", "wire_type": "float32", "units": "A"}
        ]
    }
    doc["commands"][0]["binding"]["response_pattern"] = "(?P<voltage>.+),(?P<current>.+)"
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_output_array_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["commands"][0]["output"] = {
        "kind": "array",
        "elements": {"name": "sample", "description": "ADC sample", "type": "integer", "wire_type": "int16"}
    }
    doc["commands"][0]["binding"]["response_pattern"] = "(?P<value>.+)"
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_output_file_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["commands"][0]["output"] = {
        "kind": "file", "mime_type": "image/png", "file_size_bytes": 24576
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_output_none_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["commands"][0]["output"] = {"kind": "none"}
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_errors_and_examples_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["commands"][0]["errors"] = [
        {"code": "OVER_RANGE", "wire_code": -222,
         "description": "Input exceeds selected range.",
         "recovery": "Increase the range or reduce the input."}
    ]
    doc["commands"][0]["examples"] = [
        {"parameters": {}, "output": 4.998, "note": "5V reference."}
    ]
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_other_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["protocols"] = [{"id": "p0", "kind": "other", "runs_on": ["i0"]}]
    doc["commands"][0]["binding"] = {
        "protocol_id": "p0",
        "protocol_kind": "other",
        "extension": "acme.proprietary_v2",
        "details": {"opcode": 0x42, "subop": "READ"}
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_scpi_write_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["commands"][0]["binding"] = {
        "protocol_id": "p0",
        "protocol_kind": "scpi",
        "command_template": ":TRIG:SOUR IMM",
        "is_query": False,
        "terminator": "\n"
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_scpi_query_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["commands"][0]["binding"] = {
        "protocol_id": "p0",
        "protocol_kind": "scpi",
        "command_template": ":MEAS:VOLT:DC?",
        "is_query": True,
        "response_pattern": "(?P<value>[-+0-9.eE]+)",
        "terminator": "\n",
        "response_terminator": "\n",
        "timeout_ms": 5000
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_usb_tmc_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["protocols"][0]["kind"] = "usb_tmc"
    doc["commands"][0]["binding"] = {
        "protocol_id": "p0",
        "protocol_kind": "usb_tmc",
        "command_template": "*IDN?",
        "is_query": True,
        "response_pattern": "(?P<value>.+)"
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_modbus_tcp_read_holding_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["protocols"][0] = {"id": "mb", "kind": "modbus_tcp", "runs_on": ["i0"]}
    doc["commands"][0]["binding"] = {
        "protocol_id": "mb",
        "protocol_kind": "modbus_tcp",
        "function_code": 3,
        "address": 40001,
        "quantity": 2,
        "byte_order": "ABCD",
        "word_order": "AB",
        "unit_id": 1
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_modbus_rtu_write_with_template_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["protocols"][0] = {"id": "mb", "kind": "modbus_rtu", "runs_on": ["i0"]}
    doc["commands"][0]["parameters"] = [
        {"name": "register", "description": "reg", "type": "integer", "wire_type": "uint16"},
        {"name": "value", "description": "v", "type": "integer", "wire_type": "uint16"}
    ]
    doc["commands"][0]["binding"] = {
        "protocol_id": "mb",
        "protocol_kind": "modbus_rtu",
        "function_code": 6,
        "address_template": "{register}",
        "byte_order": "ABCD",
        "value_template": "{value}"
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_http_rest_get_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["protocols"][0] = {"id": "api", "kind": "http_rest", "runs_on": ["i0"]}
    doc["commands"][0]["parameters"] = [
        {"name": "channel", "description": "ch", "type": "integer"}
    ]
    doc["commands"][0]["output"] = {"kind": "scalar", "type": "number"}
    doc["commands"][0]["binding"] = {
        "protocol_id": "api",
        "protocol_kind": "http_rest",
        "method": "GET",
        "path_template": "/api/v1/channels/{channel}/voltage",
        "expected_status": [200],
        "response_extract": {"format": "json", "pointer": "/voltage"}
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_http_rest_post_with_body_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["protocols"][0] = {"id": "api", "kind": "http_rest", "runs_on": ["i0"]}
    doc["commands"][0]["parameters"] = [
        {"name": "level", "description": "level", "type": "number"}
    ]
    doc["commands"][0]["output"] = {"kind": "none"}
    doc["commands"][0]["binding"] = {
        "protocol_id": "api",
        "protocol_kind": "http_rest",
        "method": "POST",
        "path_template": "/api/v1/output",
        "headers": {"Content-Type": "application/json"},
        "request_body": {"shape": "json", "template": {"level": "{level}"}},
        "expected_status": [200, 204]
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_grpc_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["protocols"][0] = {"id": "rpc", "kind": "grpc", "runs_on": ["i0"]}
    doc["commands"][0]["output"] = {"kind": "scalar", "type": "string"}
    doc["commands"][0]["binding"] = {
        "protocol_id": "rpc",
        "protocol_kind": "grpc",
        "service": "Device",
        "method": "GetVersion",
        "request_body": {"shape": "json", "template": {}},
        "response_extract": {"format": "json", "pointer": "/version"}
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_mqtt_publish_with_response_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["protocols"][0] = {"id": "iot", "kind": "mqtt", "runs_on": ["i0"]}
    doc["commands"][0]["parameters"] = [
        {"name": "device_id", "description": "id", "type": "string"}
    ]
    doc["commands"][0]["output"] = {"kind": "scalar", "type": "number"}
    doc["commands"][0]["binding"] = {
        "protocol_id": "iot",
        "protocol_kind": "mqtt",
        "publish_topic_template": "devices/{device_id}/read",
        "payload_template": {"shape": "json", "template": {"cmd": "voltage"}},
        "qos": 1,
        "retain": False,
        "response_topic_template": "devices/{device_id}/value",
        "response_extract": {"format": "json", "pointer": "/voltage"}
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_raw_serial_struct_frame_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["interfaces"][0] = {"id": "com1", "kind": "rs232"}
    doc["protocols"][0] = {"id": "raw", "kind": "raw_serial", "runs_on": ["com1"]}
    doc["commands"][0]["parameters"] = [
        {"name": "axis", "description": "axis index", "type": "integer", "wire_type": "uint8"}
    ]
    doc["commands"][0]["output"] = {"kind": "scalar", "type": "integer", "wire_type": "int16"}
    doc["commands"][0]["binding"] = {
        "protocol_id": "raw",
        "protocol_kind": "raw_serial",
        "framing": "delimiter",
        "framing_params": {"delimiter": "\n"},
        "byte_order": "ABCD",
        "request_frame": {
            "encoding": "struct",
            "value": [
                {"name": "opcode", "wire_type": "uint8", "source": 0x10},
                {"name": "axis",   "wire_type": "uint8", "source": "axis"}
            ]
        },
        "response_frame": {
            "encoding": "struct",
            "value": [
                {"name": "value", "wire_type": "int16", "source": "value"}
            ]
        }
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_canopen_sdo_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["interfaces"][0] = {"id": "can0", "kind": "can"}
    doc["protocols"][0] = {"id": "co", "kind": "canopen", "runs_on": ["can0"]}
    doc["commands"][0]["binding"] = {
        "protocol_id": "co",
        "protocol_kind": "canopen",
        "cob_id": 0x181,
        "framing": "fixed_length",
        "byte_order": "ABCD",
        "request_frame": {
            "encoding": "struct",
            "value": [
                {"name": "command", "wire_type": "uint8", "source": 0x40},
                {"name": "index",   "wire_type": "uint16", "source": 0x1018},
                {"name": "subindex","wire_type": "uint8", "source": 0x00}
            ]
        }
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_j1939_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["interfaces"][0] = {"id": "can0", "kind": "can"}
    doc["protocols"][0] = {"id": "j", "kind": "j1939", "runs_on": ["can0"]}
    doc["commands"][0]["binding"] = {
        "protocol_id": "j",
        "protocol_kind": "j1939",
        "pgn": 65262,
        "priority": 6,
        "framing": "fixed_length",
        "byte_order": "ABCD",
        "request_frame": {"encoding": "hex", "value": "00000000FFFFFFFF"}
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_i2c_register_read_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["interfaces"][0] = {"id": "i2c0", "kind": "i2c"}
    doc["protocols"][0] = {"id": "i2c", "kind": "i2c_register", "runs_on": ["i2c0"]}
    doc["commands"][0]["output"] = {"kind": "scalar", "type": "integer", "wire_type": "uint8"}
    doc["commands"][0]["binding"] = {
        "protocol_id": "i2c",
        "protocol_kind": "i2c_register",
        "device_address": 0x48,
        "register_address": 0x01,
        "access": "read",
        "byte_count": 1,
        "framing": "none",
        "byte_order": "ABCD",
        "request_frame": {"encoding": "hex", "value": "01"}
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_spi_register_write_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["interfaces"][0] = {"id": "spi0", "kind": "spi"}
    doc["protocols"][0] = {"id": "spi", "kind": "spi_register", "runs_on": ["spi0"]}
    doc["commands"][0]["parameters"] = [
        {"name": "v", "description": "value", "type": "integer", "wire_type": "uint8"}
    ]
    doc["commands"][0]["output"] = {"kind": "none"}
    doc["commands"][0]["binding"] = {
        "protocol_id": "spi",
        "protocol_kind": "spi_register",
        "chip_select": 0,
        "register_address": 0x05,
        "access": "write",
        "byte_count": 1,
        "framing": "none",
        "byte_order": "ABCD",
        "request_frame": {
            "encoding": "struct",
            "value": [{"name": "value", "wire_type": "uint8", "source": "v"}]
        }
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_opc_ua_read_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["protocols"][0] = {"id": "ua", "kind": "opc_ua", "runs_on": ["i0"]}
    doc["commands"][0]["parameters"] = [
        {"name": "channel", "description": "ch", "type": "integer"}
    ]
    doc["commands"][0]["binding"] = {
        "protocol_id": "ua",
        "protocol_kind": "opc_ua",
        "operation": "read",
        "node_id_template": "ns=2;s=Channels.Ch{channel}.Voltage",
        "data_type": "Double"
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_snmp_get_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["protocols"][0] = {"id": "snmp", "kind": "snmp", "runs_on": ["i0"]}
    doc["commands"][0]["binding"] = {
        "protocol_id": "snmp",
        "protocol_kind": "snmp",
        "operation": "get",
        "oid_template": "1.3.6.1.2.1.1.5.0"
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_ethernet_ip_read_tag_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["protocols"][0] = {"id": "eip", "kind": "ethernet_ip", "runs_on": ["i0"]}
    doc["commands"][0]["binding"] = {
        "protocol_id": "eip",
        "protocol_kind": "ethernet_ip",
        "addressing": {"scheme": "tag", "value": "MotorSpeed"},
        "operation": "read"
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_binding_file_transfer_download_valid(schema: dict) -> None:
    doc = _skeleton()
    doc["protocols"][0] = {"id": "ft", "kind": "file_transfer", "runs_on": ["i0"]}
    doc["commands"][0]["parameters"] = [
        {"name": "remote_name", "description": "src", "type": "string", "wire_type": "ascii"}
    ]
    doc["commands"][0]["output"] = {"kind": "file", "mime_type": "image/png"}
    doc["commands"][0]["binding"] = {
        "protocol_id": "ft",
        "protocol_kind": "file_transfer",
        "mechanism": "http_download",
        "direction": "download",
        "remote_path_template": "/scope/screen?path={remote_name}",
        "transfer_mode": "binary"
    }
    errors = _validate(schema, doc)
    assert errors == [], f"unexpected errors: {[e.message for e in errors]}"


def test_example_dmm_validates(schema: dict, examples_dir: Path) -> None:
    doc = json.loads((examples_dir / "example-dmm.json").read_text())
    errors = _validate(schema, doc)
    assert errors == [], f"example-dmm.json: {[e.message for e in errors]}"


def test_example_dmm_companion_validator(examples_dir: Path) -> None:
    from schemas.tools import validate as v
    ok, errors = v.validate_document(examples_dir / "example-dmm.json")
    assert ok, f"example-dmm.json: {errors}"


def test_example_plc_validates(schema: dict, examples_dir: Path) -> None:
    doc = json.loads((examples_dir / "example-plc.json").read_text())
    errors = _validate(schema, doc)
    assert errors == [], f"example-plc.json: {[e.message for e in errors]}"


def test_example_plc_companion_validator(examples_dir: Path) -> None:
    from schemas.tools import validate as v
    ok, errors = v.validate_document(examples_dir / "example-plc.json")
    assert ok, f"example-plc.json: {errors}"


def test_example_iot_validates(schema: dict, examples_dir: Path) -> None:
    doc = json.loads((examples_dir / "example-iot.json").read_text())
    errors = _validate(schema, doc)
    assert errors == [], f"example-iot.json: {[e.message for e in errors]}"


def test_example_iot_companion_validator(examples_dir: Path) -> None:
    from schemas.tools import validate as v
    ok, errors = v.validate_document(examples_dir / "example-iot.json")
    assert ok, f"example-iot.json: {errors}"

"""Device interface JSON document validator.

Two-layer validation:
  1. JSON Schema 2020-12 (structural)
  2. Referential checks (cross-reference integrity, template parameter
     references, unique ids)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import jsonschema

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "device-interface.schema.json"

TEMPLATE_PARAM_RE = re.compile(r"(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})")

_TEMPLATE_FIELD_NAMES = {
    "command_template",
    "address_template",
    "quantity_template",
    "value_template",
    "path_template",
    "publish_topic_template",
    "response_topic_template",
    "node_id_template",
    "method_id_template",
    "oid_template",
    "remote_path_template",
    "local_path_template",
}


def load_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open() as f:
        return json.load(f)


def load_document(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return json.load(f)


def schema_validate(doc: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = jsonschema.Draft202012Validator(schema)
    out: list[str] = []
    for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path)):
        path = "/" + "/".join(str(p) for p in err.absolute_path)
        out.append(f"[schema] {path}: {err.message}")
    return out


def check_unique_ids(items: list[dict[str, Any]], label: str) -> list[str]:
    seen: dict[str, int] = {}
    errors: list[str] = []
    for i, item in enumerate(items):
        item_id = item.get("id")
        if item_id is None:
            continue
        if item_id in seen:
            errors.append(
                f"[refs] {label}[{i}].id '{item_id}' duplicates {label}[{seen[item_id]}].id"
            )
        else:
            seen[item_id] = i
    return errors


def check_protocol_refs(doc: dict[str, Any]) -> list[str]:
    protocols = {p["id"]: p for p in doc.get("protocols", []) if "id" in p}
    interfaces = {i["id"] for i in doc.get("interfaces", []) if "id" in i}
    errors: list[str] = []
    for p in doc.get("protocols", []):
        for iface_id in p.get("runs_on", []):
            if iface_id not in interfaces:
                errors.append(
                    f"[refs] protocols[id={p.get('id')}].runs_on references unknown interface '{iface_id}'"
                )
    for cmd in doc.get("commands", []):
        binding = cmd.get("binding") or {}
        pid = binding.get("protocol_id")
        pkind = binding.get("protocol_kind")
        if pid is None:
            continue
        if pid not in protocols:
            errors.append(
                f"[refs] commands[id={cmd.get('id')}].binding.protocol_id '{pid}' not in protocols"
            )
            continue
        actual_kind = protocols[pid].get("kind")
        if pkind != actual_kind:
            errors.append(
                f"[refs] commands[id={cmd.get('id')}].binding.protocol_kind '{pkind}' "
                f"!= protocols[id={pid}].kind '{actual_kind}'"
            )
    return errors


def _iter_template_strings(obj: Any, prefix: str = ""):
    if isinstance(obj, dict):
        for k, val in obj.items():
            kp = f"{prefix}.{k}" if prefix else k
            if isinstance(val, str) and k in _TEMPLATE_FIELD_NAMES:
                yield kp, val
            elif isinstance(val, dict) or isinstance(val, list):
                yield from _iter_template_strings(val, kp)
            elif isinstance(val, str) and k.endswith("_template"):
                yield kp, val
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from _iter_template_strings(item, f"{prefix}[{i}]")


def check_template_params(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for cmd in doc.get("commands", []):
        param_names = {p["name"] for p in cmd.get("parameters", []) if "name" in p}
        binding = cmd.get("binding") or {}
        for path, value in _iter_template_strings(binding, prefix="binding"):
            for match in TEMPLATE_PARAM_RE.finditer(value):
                ref = match.group(1)
                if ref not in param_names:
                    errors.append(
                        f"[refs] commands[id={cmd.get('id')}].{path} references unknown parameter '{ref}'"
                    )
    return errors


def check_scpi_response_groups(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for cmd in doc.get("commands", []):
        binding = cmd.get("binding") or {}
        if binding.get("protocol_kind") not in ("scpi", "usb_tmc"):
            continue
        if not binding.get("is_query"):
            continue
        pattern = binding.get("response_pattern")
        if not pattern:
            continue
        output = cmd.get("output") or {}
        if output.get("kind") in (None, "none"):
            continue
        if output.get("kind") == "record":
            expected = {f["name"] for f in output.get("fields", []) if "name" in f}
        else:
            expected = {"value"}
        try:
            compiled = re.compile(pattern)
        except re.error as e:
            errors.append(
                f"[refs] commands[id={cmd.get('id')}].binding.response_pattern invalid regex: {e}"
            )
            continue
        actual = set(compiled.groupindex)
        missing = expected - actual
        if missing:
            errors.append(
                f"[refs] commands[id={cmd.get('id')}].binding.response_pattern "
                f"missing named groups: {sorted(missing)}"
            )
    return errors


def validate_document(doc_path: Path) -> tuple[bool, list[str]]:
    schema = load_schema()
    doc = load_document(doc_path)
    errors: list[str] = []
    errors.extend(schema_validate(doc, schema))
    if errors:
        return False, errors
    errors.extend(check_unique_ids(doc.get("interfaces", []), "interfaces"))
    errors.extend(check_unique_ids(doc.get("protocols", []), "protocols"))
    errors.extend(check_unique_ids(doc.get("commands", []), "commands"))
    errors.extend(check_protocol_refs(doc))
    errors.extend(check_template_params(doc))
    errors.extend(check_scpi_response_groups(doc))
    return (len(errors) == 0), errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    args = parser.parse_args()
    ok, errors = validate_document(args.document)
    if ok:
        print(f"OK: {args.document}")
        return 0
    print(f"FAIL: {args.document}", file=sys.stderr)
    for err in errors:
        print(f"  {err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

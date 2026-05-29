# Device Interface Schema

JSON Schema (draft 2020-12) describing a generic device interface — its
identifying information, physical interfaces, logical protocols, and every
command the device offers with enough binding detail to drive it from code.

See `docs/superpowers/specs/2026-05-28-device-interface-schema-design.md`
for the design rationale.

## Files

- `device-interface.schema.json` — the schema.
- `tools/validate.py` — companion validator (CLI + library).
- `examples/example-*.json` — three worked examples (DMM, PLC, IoT hub).
- `examples/invalid/*.json` — fixtures that must fail validation.
- `tests/` — pytest test suite.

## Validating a Document

Two layers; both must pass:

1. **JSON Schema (structural)** — shape, required fields, enums, ranges,
   the tagged-union `binding` variant.
2. **Companion validator (referential)** — id uniqueness, protocol/interface
   cross-references, `{param}` substitutions reference real parameters, SCPI
   `response_pattern` named groups match output `fields`.

```bash
python -m pip install -r requirements.txt
python -m schemas.tools.validate path/to/device.json
```

Exit code: 0 on success, 1 on failure (errors printed to stderr).

## Top-Level Structure

```json
{
  "schema_version": "1.0.0",
  "device":     { "manufacturer": "...", "model": "...", ... },
  "interfaces": [ { "id": "...", "kind": "ethernet" | "usb" | ... } ],
  "protocols":  [ { "id": "...", "kind": "scpi" | "modbus_tcp" | ...,
                    "runs_on": ["<interface id>", ...] } ],
  "commands":   [ { "id": "...", "name": "...", "description": "...",
                    "parameters": [...], "output": {...},
                    "binding": { "protocol_id": "...",
                                 "protocol_kind": "scpi" | ...,
                                 /* protocol-specific fields */ } } ]
}
```

A command's `binding` is discriminated on `protocol_kind`. Each variant has
its own required fields — see the design spec for the full list.

## Extending

Two explicit extension points; do not silently add unknown keys.

1. **`extensions` field** on `device`, each `interface`, each `protocol`, and
   each `command` — an open object for vendor/tool metadata. Convention:
   vendor-namespace your keys (`"acme.foo": ...`, `"keysight.lxi": ...`).
2. **`"other"` binding variant** — for protocols not yet covered. Required
   fields: `protocol_id`, `protocol_kind: "other"`, `extension`
   (vendor-namespaced kind), `details` (open object).

When the time comes to promote an `other`-shaped binding to a first-class
protocol, add a `$defs/bindings/<kind>` entry, extend `binding.oneOf`, and
add positive + negative tests under `tests/`.

## Versioning

Instances carry `schema_version` (semver). The schema file's `$id` includes
its version. Major bumps are breaking; minor bumps add optional fields, new
enum members, or new binding variants; patch bumps are documentation only.
Consumers must explicitly upgrade — no auto-acceptance of newer minor
versions.

## Running the Test Suite

```bash
python -m pytest schemas/tests/ -v
```

All three example documents and four invalid fixtures are exercised; the
validator's unit tests cover each referential check independently.

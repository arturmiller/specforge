# Requirement Verification Report: calendar@1.0.0

## Scope

This report covers only the formalized, machine-verifiable requirements listed below for the recorded software revision. It makes no general legal or regulatory compliance claim.

- Resolved specification: `sha256:e1c1975814c6e04df009a0651e93a1bf47a6ead55f21276815ac81df33f87950`
- Software revision: `2e46d2bd66c8358ae7fd42a237dd5c03b29ee5f8+app.sha256.02d6982d4ac42533`

## Requirements

| Requirement instance | Kind | Source | Status | Pattern | Verification | Evidence |
|---|---|---|---|---|---|---|
| `DATA-001@operation.create_event` | derived | `calendar-invariants@1.0.0#event-time` | **VERIFIED** | `fastapi/event-interval-validation` | `TEST-DATA-001@operation:create_event` | `evidence-b0308bc386c56ce523e8` |
| `DATA-001@operation.update_event` | derived | `calendar-invariants@1.0.0#event-time` | **VERIFIED** | `fastapi/event-interval-validation` | `TEST-DATA-001@operation:update_event` | `evidence-8df4b15bad1ae98f7a1f` |
| `OBS-001@operation.read_event` | declared | `observability-policy@1.0.0#resource-access` | **VERIFIED** | `fastapi/audit-resource-access` | `TEST-OBS-001@operation:read_event` | `evidence-347cbfbacec74e5ea812` |
| `PLATFORM-001@operation.read_event` | declared | `platform-policy@1.0.0#traffic` | **VERIFIED** | `fastapi/read-rate-limit` | `TEST-PLATFORM-001@operation:read_event` | `evidence-f6fbb140e19f2c710c19` |
| `PRIVACY-001@operation.create_event` | derived | `privacy-policy@1.0.0#response-minimization` | **VERIFIED** | `fastapi/declared-response-schema` | `TEST-PRIVACY-001@operation:create_event` | `evidence-8425251b28d7431c16b4` |
| `PRIVACY-001@operation.read_event` | derived | `privacy-policy@1.0.0#response-minimization` | **VERIFIED** | `fastapi/declared-response-schema` | `TEST-PRIVACY-001@operation:read_event` | `evidence-927b9e627729edcc5339` |
| `PRIVACY-001@operation.update_event` | derived | `privacy-policy@1.0.0#response-minimization` | **VERIFIED** | `fastapi/declared-response-schema` | `TEST-PRIVACY-001@operation:update_event` | `evidence-bf97ed37829bf2f73c53` |
| `PRODUCT-001@operation.create_event` | declared | `calendar-product@1.0.0#create` | **VERIFIED** | `fastapi/calendar-crud` | `TEST-PRODUCT-001@operation:create_event` | `evidence-1501bc5abd836a0ce783` |
| `PRODUCT-002@operation.read_event` | declared | `calendar-product@1.0.0#read` | **VERIFIED** | `fastapi/calendar-crud` | `TEST-PRODUCT-002@operation:read_event` | `evidence-b1b9c00db3183c321888` |
| `PRODUCT-003@operation.update_event` | declared | `calendar-product@1.0.0#update` | **VERIFIED** | `fastapi/calendar-crud` | `TEST-PRODUCT-003@operation:update_event` | `evidence-83f44dfb22e6d3e8466f` |
| `PRODUCT-004@operation.delete_event` | declared | `calendar-product@1.0.0#delete` | **VERIFIED** | `fastapi/calendar-crud` | `TEST-PRODUCT-004@operation:delete_event` | `evidence-5e2d4204b4c504c1c68e` |
| `SEC-001@operation.create_event` | derived | `security-policy@1.0.0#authenticated-personal-data` | **VERIFIED** | `fastapi/bearer-ownership` | `TEST-SEC-001@operation:create_event` | `evidence-e1f7434e883b24ee02b3` |
| `SEC-001@operation.delete_event` | derived | `security-policy@1.0.0#authenticated-personal-data` | **VERIFIED** | `fastapi/bearer-ownership` | `TEST-SEC-001@operation:delete_event` | `evidence-5f6c3b8ad000831a26cd` |
| `SEC-001@operation.read_event` | derived | `security-policy@1.0.0#authenticated-personal-data` | **VERIFIED** | `fastapi/bearer-ownership` | `TEST-SEC-001@operation:read_event` | `evidence-cfec46446d70bdbb19ad` |
| `SEC-001@operation.update_event` | derived | `security-policy@1.0.0#authenticated-personal-data` | **VERIFIED** | `fastapi/bearer-ownership` | `TEST-SEC-001@operation:update_event` | `evidence-f23f7ef16a689d6c8695` |
| `SEC-002@operation.delete_event` | derived | `security-policy@1.0.0#ownership` | **VERIFIED** | `fastapi/bearer-ownership` | `TEST-SEC-002@operation:delete_event` | `evidence-72617a8b838e83a12264` |
| `SEC-002@operation.read_event` | derived | `security-policy@1.0.0#ownership` | **VERIFIED** | `fastapi/bearer-ownership` | `TEST-SEC-002@operation:read_event` | `evidence-7ac705e4dc1c80cde9b5` |
| `SEC-002@operation.update_event` | derived | `security-policy@1.0.0#ownership` | **VERIFIED** | `fastapi/bearer-ownership` | `TEST-SEC-002@operation:update_event` | `evidence-f66112c91b48fd2f90f4` |

## Knowledge packages

- `calendar@1.0.0` — `sha256:49efd806b5ac6aba9da26bb6d1d30a8e320fb0a18263761013b016b20dee8694`
- `data@1.0.0` — `sha256:c08fde896bcaec7ecab89afc449554e9ed0a2b662630181650528ba18240f991`
- `observability@1.0.0` — `sha256:4ad231577b10830a45325ac592473e443e3da8c64c3705eae2be0a2156290b20`
- `platform@1.0.0` — `sha256:a6a98ece23dc758f75f874df2f9c16265e792623f13f84a6051a972fc0a3c91b`
- `privacy@1.0.0` — `sha256:e989b7152fb30606fa336ed6a89d800130a230d050ff9aafc3eaa8b15ac11ea6`
- `security@1.0.0` — `sha256:3506b16e7cbe3a90795a2c9e2ff810ffb06448ceadec0823a1bd8c2ef515e2ef`

## Evidence limitations

A passing integration test proves the recorded observation for the specified input, application revision and execution environment. It is not a mathematical proof of all possible executions.

# AgriNet Protocol v1.0

**An open schema for interoperable agricultural intelligence between Indian states.**

Any state (or country) joins the federation by deploying one container that speaks this protocol. There is no central server: nodes are peers that push and pull signed¹ payloads over plain HTTPS + JSON. The canonical machine-readable schema is the pydantic models in `backend/app/models/protocol.py`; every node also serves its OpenAPI spec at `/docs` and `/openapi.json`.

¹ *Signatures are roadmap (v1.1) — the hackathon prototype trusts configured peers.*

## Design principles

1. **Open & minimal** — five resource types, plain REST, JSON Schema. A state IT team can implement it in a day in any language.
2. **Federated, not centralized** — each state owns its node, its data, its farmers' trust. Only anonymized, aggregate signals cross state lines.
3. **Idempotent exchange** — every shared object carries a globally unique `id`; receiving a duplicate is a no-op. Push retries are safe.
4. **Privacy by construction** — the schema has no fields for personal identifiers or precise coordinates. District is the finest location granularity.

## Resources

### Alert — cross-state early warning

| field | type | notes |
|---|---|---|
| id | string (uuid) | idempotency key |
| origin_state | string | e.g. `TS` |
| disease | string | |
| crop | string? | |
| district | string? | coarsest useful geography |
| severity | `low\|medium\|high` | |
| report_count | int ≥ 1 | evidence: confirmed diagnoses |
| window_days | int ≥ 1 | window the count covers |
| message | string? | human-readable summary |
| created_at | datetime | ISO-8601 UTC |

### Insight — shareable agronomic finding

`{ id, state_id, district?, crop?, type: practice|yield|pest|weather|market, summary, evidence?, created_at }`

### Peer — federation member

`{ state_id, name, base_url, last_sync? }`

### ModelRegistryEntry — shared model catalog

`{ name, version, task, trained_by, artifact_url?, published_at }`

States can publish fine-tuned models (e.g. a Gemma disease classifier trained on Telangana leaf images) for other states to adopt — cooperation on models, not just data.

### Health

`{ status: "ok", state_id, state_name, protocol_version }`

## Endpoints (every node)

| method | path | purpose |
|---|---|---|
| GET | `/v1/health` | liveness + protocol version |
| GET | `/v1/alerts` | list alerts known to this node (local + received) |
| POST | `/v1/alerts` | receive an alert pushed by a peer (idempotent, 202) |
| GET | `/v1/insights` | list shareable insights |
| POST | `/v1/insights` | receive an insight (idempotent, 202) |
| GET | `/v1/peers` | this node's configured peers |
| GET | `/v1/models` | shared model registry |

## Exchange semantics

- **Push:** when a node creates an Alert (e.g. its outbreak detector fires), it POSTs the alert to every configured peer, retrying up to 3 times with backoff. Delivery is best-effort; a down peer never blocks farmer-facing traffic.
- **Idempotency:** receivers upsert by `id` and answer `{accepted: true, duplicate: bool}`.
- **Peer configuration:** a comma-separated `PEERS` env var of base URLs (a signed peer registry is the v1.1 roadmap).

## Worked example

Telangana's node confirms 3 brown-planthopper diagnoses in Warangal within 7 days → it creates:

```json
{
  "id": "3f8e…",
  "origin_state": "TS",
  "disease": "Brown planthopper (Nilaparvata lugens)",
  "crop": "paddy",
  "district": "Warangal",
  "severity": "high",
  "report_count": 3,
  "window_days": 7,
  "message": "Brown planthopper outbreak in paddy: 3 confirmed reports in Warangal district (Telangana) within 7 days.",
  "created_at": "2026-08-22T09:14:03Z"
}
```

and POSTs it to Odisha's node, whose officer dashboard immediately shows *"Early warning from Telangana (AgriNet federation)"* — before the pest reaches Odisha's border districts.

## Versioning

`protocol_version` is returned by `/v1/health` and in list envelopes. Additive changes bump the minor version; breaking changes get a new path prefix (`/v2`).

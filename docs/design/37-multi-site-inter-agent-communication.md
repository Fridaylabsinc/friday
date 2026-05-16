# 37. Multi-Site Inter-Agent Communication

## Why Multi-Site

A single Friday installation runs on a single Frappe site. But real organizations have:
- Multiple Frappe sites (e.g. one per company, one per region)
- Multiple businesses where parent and subsidiaries each run separate Friday instances
- Friday running locally for a customer alongside FridayLabs cloud services
- Partner Friday instances that need to coordinate (supplier ↔ customer Friday talking directly)

We need agents in different Friday sites to discover, authenticate, and exchange messages with each other — safely.

## Agent Communication Protocol (ACP)

ACP defines a minimal, secure, async messaging protocol between Friday sites.

### Transport
- HTTPS only (no plaintext HTTP)
- mTLS by default — each Friday site has its own X.509 certificate
- Optionally: HTTP/2 multiplexing for high-throughput pairs
- Message body: JSON

### Message Structure
```json
{
  "version": "acp/1.0",
  "message_id": "uuid-v4",
  "conversation_id": "uuid-v4",
  "sender": {
    "site": "https://friday-a.example.com",
    "agent": "procurement-agent",
    "instance_id": "uuid"
  },
  "recipient": {
    "site": "https://friday-b.example.com",
    "agent": "sales-agent"
  },
  "intent": "purchase_order_announce",
  "payload": {...},
  "signed_at": "2026-04-12T14:23:11Z",
  "signature": "ed25519-sig-base64"
}
```

### Intents
A small, versioned catalog of intents. Phase 1 includes:
- `purchase_order_announce` — supplier-side Friday announces an incoming PO from customer-side Friday
- `shipment_notification` — supplier notifies customer of dispatch
- `invoice_announce` — supplier announces invoice availability
- `payment_confirmation` — customer announces payment sent
- `inventory_query` — request stock availability from a partner
- `inventory_response` — answer to query
- `escalation_handoff` — escalate a problem to a partner's human supervisor
- `acknowledgment` — generic ACK with optional payload

Intents are namespaced (`erpnext.purchase_order_announce`) and versioned (`v1`).

## DocType: Friday Partner Site

Records each known partner site:

Fields:
- `site_name` (Data, unique) — e.g. "Acme Suppliers Friday"
- `site_url` (Data) — base URL
- `public_key` (Long Text) — for signature verification
- `certificate_fingerprint` (Data) — mTLS cert pin
- `trust_level` (Select: Untrusted, Verified, Trusted)
- `allowed_intents` (child table) — which intents are permitted from this site
- `rate_limit_per_minute` (Int)
- `last_heartbeat_at` (Datetime)
- `status` (Select: Active, Suspended, Revoked)

## Service Discovery

How does Friday A find Friday B?

Three modes:

### Mode 1: Manual
Supervisor adds a Partner Site record by hand with URL, public key, and certificate fingerprint exchanged out-of-band (email, phone confirmation).

This is Phase 1.

### Mode 2: Well-Known Endpoint
Each Friday site exposes `https://{site}/.well-known/friday-acp` returning:
```json
{
  "site_name": "Acme Suppliers Friday",
  "public_key": "ed25519-pubkey-base64",
  "supported_intents": [...],
  "contact": "ops@acme.com",
  "trust_anchors": [...]
}
```

A supervisor can paste a partner's URL; Friday auto-fetches and presents the discovered config for approval.

### Mode 3: Registry (Phase 4)
A FridayLabs-hosted partner registry. Sites can publish themselves, others can search. Discovery is opt-in and auditable.

## Authentication

mTLS at the transport layer ensures only certified sites can connect. Each message also carries an Ed25519 signature over the canonical message body, verified using the partner's public key from the Partner Site record.

Replay protection: each message has a `message_id`; Friday rejects duplicate IDs within 24 hours.

## Authorization

When a message arrives:
1. Verify TLS client cert against Partner Site.fingerprint.
2. Verify Ed25519 signature.
3. Look up Partner Site; check status (Active).
4. Check `intent` is in `allowed_intents` for this partner.
5. Check rate limit (rolling 60-second window).
6. If all pass → enqueue for processing.
7. If any fail → reject with appropriate code, log.

## Message Processing

Incoming messages enqueue to a Frappe RQ queue. A worker:
1. Resolves intent handler (`friday.acp.handlers.{intent_name}`).
2. Invokes the handler with the message.
3. Handler is intent-specific — e.g. `purchase_order_announce` handler creates a Sales Order in local ERPNext from the incoming PO data.
4. Handler emits an acknowledgment message back to the sender.

Intent handlers run in the same sandbox isolation as skills (doc 24). They're code Friday maintainers ship and review.

## Rate Limiting

Per-partner rate limits prevent a misbehaving or hostile partner from overwhelming us:
- Default: 60 messages/minute per partner
- Burst: 10 messages in 5 seconds allowed
- Sustained excess: messages 429'd, partner notified

Limits configurable per partner site.

## Escalation Handoff

A special intent: `escalation_handoff`. When agent A can't resolve an issue and needs partner site B's human supervisor:

1. Agent A composes an escalation message with context.
2. Sends to partner B.
3. B's Friday creates an Agent Task with priority "External Escalation" in B's War Room.
4. B's supervisor sees the escalation, can respond by sending a message back via ACP.
5. Conversation continues async until resolved.

This formalizes B2B human ↔ human ↔ agent collaboration.

## Privacy

Outbound messages are reviewed before leaving:
- Personal data redaction policies applied (e.g. internal employee IDs replaced with opaque tokens)
- Sensitive memory entries blocked from being included
- Supervisor can configure per-partner what fields are includable

A "data sharing audit" log records exactly what content went to whom and when. GDPR/DPDPA discovery cost is small because everything is queryable.

## Trust Levels

- **Untrusted:** Friday only sends acknowledgments to messages; doesn't initiate. Useful for new partners during a verification period.
- **Verified:** Standard interaction. Most partners sit here.
- **Trusted:** Reduced approval gates; certain autopilot actions can proceed without re-approval per message. Reserved for long-established partners.

Trust level changes are supervisor decisions, logged.

## Conflict Resolution

When two sites disagree (e.g. supplier says shipped, customer says not received):
1. Both agents flag the discrepancy.
2. Escalation handoff initiated.
3. Conversation continues until resolution.
4. Resolution recorded as memory entries (Reflective category) in both sites.
5. Pattern repeats → enters the learning loop (doc 22) for future automation.

## Network Topology

Phase 1: pairwise direct connections only. No relays, no brokers.

Phase 4: optional FridayLabs cloud relay for sites behind NAT or with intermittent connectivity. Messages queue at the relay, deliver when destination reachable. Relay never sees plaintext (end-to-end signed; payload can be additionally encrypted).

## Observability

Per partner connection:
- Messages sent/received per hour
- Latency p50, p99
- Error rate per intent
- Last successful exchange timestamp

Visible in Friday Operations Dashboard.

## Failure Modes

Partner unreachable:
- Outbound messages retry with exponential backoff (5min, 15min, 1h, 6h, 24h)
- After 24h of unreachability, partner marked Status=Suspended and supervisor notified
- Conversation marked stalled; agent may pursue alternative paths

Partner sends malformed message:
- Reject with HTTP 400 + reason
- Log for investigation
- Repeated malformed messages → automatic Status=Suspended

Partner sends apparently malicious message (impossible intent, oversized payload, etc.):
- Drop
- Log with high priority
- Notify supervisor
- After 3 in 24h → automatic Status=Revoked, requires manual reinstatement

## Phase 1 Scope

NOT in Phase 1. Friday Phase 1 is single-site only.

## Phase 2 Scope

Phase 2 ships:
- Partner Site DocType (manual entry only)
- ACP protocol implementation
- 4 core intents: PO announce, shipment notify, invoice announce, payment confirm
- mTLS + Ed25519 signature verification
- Rate limiting
- Basic escalation handoff

## Phase 3 Scope

Phase 3 ships:
- Well-known endpoint discovery
- Full intent catalog
- Trust levels
- Data sharing audit
- Failure mode handling

## Phase 4 Scope

Phase 4 ships:
- Optional cloud relay
- Partner registry (FridayLabs hosted)
- Multi-party conversations (3+ sites)
- Inter-site analytics (with consent)

## Open Questions

1. Intent versioning — when a new intent version supersedes an old one, how long do we support both? 24 months minimum after the new version ships.
2. Message size limit — what's a reasonable max? 1MB payload Phase 2; larger needs alternative (file transfer with checksum and out-of-band signal).
3. Inter-site identity beyond the Friday installation — when humans need to be addressable across sites, do we federate user IDs? Out of scope until at least Phase 4.
4. Compliance with regional data residency (Indian DPDPA, EU GDPR)? Each site enforces its own residency; ACP only carries what local policy permits.

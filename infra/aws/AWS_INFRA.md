# AWS GPU infrastructure

Live AWS setup for the Warsaw Model Trainers / Tarasiuk Lab hackathon.

This is the version-controlled handoff document for humans and agents using the
shared GPU infrastructure. Values here were verified from the AWS console on
2026-09-26 (Europe/Warsaw). Do not invent balances, instance IDs, IPs, or quota
request IDs; update them only from AWS.

Operational note: agents may also keep live session notes under
`/workspace/hackathon/notes/` on the shared box. That path is an operational
mirror, not a repo content requirement; this file is the canonical repo doc.

## Account and billing snapshot

| Field | Value |
| --- | --- |
| Console identity | `t1 development` |
| Account ID | `779846788838` |
| Region | `us-east-1` |

### Credits

| Metric | Value |
| --- | --- |
| Remaining credits | **$98,383.45** |
| Used credits | **$1,616.55** |
| Estimated remaining credits | **$98,355.81** |
| Estimated used credits | **$1,644.19** |
| Active credits | **1** |
| Credit expiry | **TBD** |

## Exam constraints

These constraints drive model and instance choices for the hackathon:

- Open weights must be **<= 8 GB on disk**
- RAG is excluded from that cap
- LoRA adapters are excluded from that cap
- Exam answering must remain **offline**

## SSH access for every GPU VM

Public key to install on every GPU VM launched for this effort:

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDM8s/6f/WZTkctzZ+Gl6Pl+gIcLtMbTtVX2G8v7iMLY Orest-Noninteractive
```

Committed public key file: [`orest-noninteractive.pub`](./orest-noninteractive.pub)

| Setting | Value |
| --- | --- |
| EC2 key pair name | `Orest-Noninteractive` |
| Scope | Every GPU VM used for the hackathon |

Example SSH command once a VM has a public address:

```bash
ssh -i ~/.ssh/Orest-Noninteractive ubuntu@<PUBLIC_IP_OR_DNS>
```

The private key must stay off-repo. Never commit private keys, IAM access keys,
session tokens, or other secrets.

## Instance naming and launch policy

Use this naming plan for GPU EC2 instances:

- `hackathon-gpu-max`
- `hackathon-gpu-max-N`

When quotas and capacity allow, prefer the largest available **On-Demand** GPU
instance in this order:

1. `p5`
2. `p4d`
3. `g6`
4. `g5`

Aggressive Service Quotas increase requests are in flight to make that possible.

## Current instance tracker

Fill these rows from the console or CLI when instances are launched.

| Name | Instance ID | Instance type | Availability Zone | Public IP / DNS | State | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `hackathon-gpu-max` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | First shared GPU box |
| `hackathon-gpu-max-2` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | Add rows as needed |

## Quota request tracker

Record exact request IDs and outcomes here once visible.

| Region | Family / quota | Current value | Requested value | Request ID | Status |
| --- | --- | --- | --- | --- | --- |
| `us-east-1` | `TBD` | `TBD` | `TBD` | `TBD` | In flight |

## Operating notes for humans and agents

- Treat this file as the repo-backed source of truth for the live AWS setup.
- Use `/workspace/hackathon/notes/` for session-specific operational notes that
  should be visible on the shared box even before they are committed here.
- Keep placeholders clearly marked as `TBD` until they are verified.
- Do not commit secrets. Public keys are fine; private keys are not.

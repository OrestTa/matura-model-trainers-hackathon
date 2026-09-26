# AWS GPU infrastructure for the Warsaw Model Trainers / Tarasiuk Lab hackathon

Last verified from the AWS console: 2026-09-26 (Europe/Warsaw)

This document records the live AWS setup that humans and agents should use for
the hackathon GPU VMs. Keep it limited to verified console facts and clearly
marked placeholders; do not invent balances, instance IDs, public IPs, or quota
request IDs.

## AWS account snapshot

| Field | Value |
| --- | --- |
| Console identity | `t1 development` |
| Account ID | `779846788838` |
| Region | `us-east-1` |

## Credits snapshot

| Metric | Value |
| --- | --- |
| Remaining credits | `$98,383.45` |
| Used credits | `$1,616.55` |
| Estimated remaining credits | `$98,355.81` |
| Estimated used credits | `$1,644.19` |
| Active credits | `1` |
| Credit expiry | `TBD` |

## GPU VM access

Use the same SSH public key on every GPU VM launched for this hackathon.

- EC2 key pair name: `Orest-Noninteractive`
- Committed public key file: [`orest-noninteractive.pub`](./orest-noninteractive.pub)

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDM8s/6f/WZTkctzZ+Gl6Pl+gIcLtMbTtVX2G8v7iMLY Orest-Noninteractive
```

Example connection pattern after a VM exists:

```bash
ssh -i ~/.ssh/Orest-Noninteractive <user>@<public-ip-or-dns>
```

Never commit private keys, IAM access keys, session tokens, or other secrets.

## Instance naming and capacity plan

- Primary name: `hackathon-gpu-max`
- Additional boxes: `hackathon-gpu-max-N`
- Capacity preference: largest GPU On-Demand available under quota, in this order:
  `p5` -> `p4d` -> `g6` -> `g5`
- Service Quotas status: aggressive quota increase requests are in flight

### Current GPU VM inventory

Fill in the live values once instances exist or are confirmed.

| Name | Instance ID | Instance type | Availability Zone | Public IP / DNS | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `hackathon-gpu-max` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | Prefer the largest available On-Demand GPU |
| `hackathon-gpu-max-N` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | Add rows as more boxes are launched |

### Quota request tracker

Quota request IDs may stay as placeholders until AWS returns them.

| Quota family or request | Request ID | Status | Notes |
| --- | --- | --- | --- |
| `p5 / p4d / g6 / g5` capacity increases | `TBD` | `In flight` | Track the largest usable GPU family first |

## Hackathon model constraints

- Open weights must be `<= 8 GB` on disk
- RAG and LoRA are excluded from that size limit
- Exam answering must stay offline

## Shared operational notes

- Agents use `/workspace/hackathon/notes/` as a shared-box operational mirror.
  Treat that path as an operational note location, not as a requirement that repo
  content live there.
- This repository document is the versioned reference for committed AWS infra
  facts; use clearly marked `TBD` placeholders until console values are known.

## Safety rules

- Do not commit secrets, IAM keys, private keys, or copied console credentials.
- Keep instance IDs, public IPs, and quota request IDs as `TBD` until they are
  confirmed from AWS.

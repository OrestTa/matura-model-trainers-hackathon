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
| Account ID | (redacted) |
| Region | `us-east-1` |

### Credits

| Metric | Value |
| --- | --- |
| Credit name | **AWS Activate - Andreessen Horowitz** |
| Status | **Active** |
| Issued credits | **$100,000.00** |
| Remaining credits | **$98,383.45** |
| Used credits | **$1,616.55** |
| Estimated remaining credits | **$98,355.81** |
| Estimated used credits | **$1,644.19** |
| Active credits | **1** |
| Credit start date | **09/01/2024** |
| Credit expiry | **Credits table: 09/30/2026; detail page also shows 10/1/2026** |
| Applicable services shown | **EC2, SageMaker, VPC, Data Transfer** |
| Exclusions shown | **None displayed** |

Operational note: plan around AWS Activate credits expiring around
**2026-09-30**.

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
| Key type | `ed25519` |
| Key pair status | Imported |
| Scope | Every GPU VM used for the hackathon |
| Launch wizard security group note | TCP 22 from `0.0.0.0/0`; public-access warning shown; no instance created |

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

## EC2 quota snapshot (`us-east-1`)

| Quota | Verified value |
| --- | --- |
| Running On-Demand G and VT instances | **0** |
| Running On-Demand P instances | **0** |
| Family-specific P4 / P5 / G5 / G6 / G4dn / Trn1-related quotas shown in console | **0** |

## Quota request tracker

| Region | Service / quota | Requested value | Request / case | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| `us-east-1` | EC2 Running On-Demand G and VT | `1024 vCPUs` | `179041353300510` | Pending/Case Opened | Request submitted |
| `us-east-1` | EC2 Running On-Demand P | `1024 vCPUs` | `179041340000396` | Pending/Case Opened | Request submitted |
| `us-west-2` | EC2 Running On-Demand G and VT | `1024 vCPUs` | `179041346400081` | Case Closed | Intentionally canceled to free a request slot |
| `us-west-2` | EC2 Running On-Demand G and VT | `32 vCPUs` | `179041702400280` | Pending | Small ASAP ask |
| `us-west-2` | EC2 Running On-Demand P | `1024 vCPUs` | `179041351000024` | Pending/Case Opened | Request submitted |
| `eu-west-1` | EC2 Running On-Demand G and VT | `32 vCPUs` | `179041759900212` | Pending | Small ask |
| `us-east-2` | EC2 Running On-Demand G and VT | `32 vCPUs` | `179041728600007` | Pending | Small ask |
| `us-east-1` | SageMaker `ml.p5.48xlarge` training | `8` | `TBD` | Blocked | Quota-request limit hit while prior request is open |

Region-scan note: Applied quota remained `0` for On-Demand / Spot G and VT
plus P across 9 scanned regions. Additional small `G/VT 32` requests may still
be filed in other regions; case IDs are not listed here until verified.

## Launch attempts (`us-east-1`)

No instance IDs were created from these attempts.

| Instance type | Result | Reason shown | Linux hourly price shown |
| --- | --- | --- | --- |
| `p5.48xlarge` | Failed | Insufficient capacity | `~$55.04/hr` |
| `p4d.24xlarge` | Failed | vCPU limit 0 | `~$21.96/hr` |
| `g6e.48xlarge` | Failed | vCPU limit 0 | `~$30.13/hr` |

## Operating notes for humans and agents

- Treat this file as the repo-backed source of truth for the live AWS setup.
- Use `/workspace/hackathon/notes/` for session-specific operational notes that
  should be visible on the shared box even before they are committed here.
- Keep placeholders clearly marked as `TBD` until they are verified.
- Do not commit secrets. Public keys are fine; private keys are not.

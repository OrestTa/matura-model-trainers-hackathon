# AWS GPU infra - Tarasiuk Lab / Warsaw Model Trainers

Last updated: 2026-09-26 ~12:27 (Europe/Warsaw)

## Account
- Console: `t1 development` - Account (redacted) - Region focus `us-east-1` (+ quota asks in `us-west-2`)

## Credits - AWS Activate - Andreessen Horowitz

| | |
| --- | --- |
| Issued | $100,000.00 |
| Used | $1,616.55 |
| Remaining | $98,383.45 |
| Est. used / remaining | $1,644.19 / $98,355.81 |
| Start | 2024-09-01 |
| Expiry | 2026-09-30 (detail page also shows 2026-10-01) |
| Services | Includes EC2, SageMaker, VPC, Data Transfer (no exclusions shown) |

## SSH (every GPU VM)
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDM8s/6f/WZTkctzZ+Gl6Pl+gIcLtMbTtVX2G8v7iMLY Orest-Noninteractive
```
- EC2 key pair imported: `Orest-Noninteractive`
- Repo mirror: https://github.com/OrestTa/matura-model-trainers-hackathon/pull/4

## Quotas

| Region | Quota | Applied | Requested | Status |
| --- | --- | --- | --- | --- |
| us-east-1 | Running On-Demand G and VT | 0 | 1024 vCPU | Case Opened `179041353300510` |
| us-east-1 | Running On-Demand P | 0 | 1024 vCPU | Case Opened `179041340000396` |
| us-west-2 | Running On-Demand G and VT | 0 | 32 vCPU | Case Opened `179041702400280` |
| us-west-2 | Running On-Demand P | 0 | 1024 vCPU | Case Opened `179041351000024` |
| us-west-2 | Running On-Demand G and VT (prior) | 0 | 1024 vCPU | Case Closed `179041346400081` (canceled to free slot for small ask) |
| us-east-2 | Running On-Demand G and VT | 0 | 32 vCPU | Case Opened `179041728600007` |
| eu-west-1 | Running On-Demand G and VT | 0 | 32 vCPU | Case Opened `179041759900212` |
| eu-central-1 | Running On-Demand G and VT | 0 | 32 vCPU | Case Opened `179041780500011` |
| ap-southeast-1 | Running On-Demand G and VT | 0 | 32 vCPU | Case Opened `179041804600760` |
| ap-northeast-2 | Running On-Demand G and VT | 0 | 32 vCPU | Case Opened `179041816100621` |
| us-east-1 | SageMaker ml.p5.48xlarge for training | 0 | 8 | Blocked (request limit) |

## Launch attempts (none running)

| Type | Result |
| --- | --- |
| p5.48xlarge | Insufficient capacity (~$55.04/hr Linux) |
| p4d.24xlarge | vCPU limit 0 (~$21.96/hr) |
| g6e.48xlarge | vCPU limit 0 (~$30.13/hr) |

Last quiet watch check: 2026-09-26 ~12:27 Europe/Warsaw - Applied still 0 for G/VT and P in us-east-1, us-west-2, us-east-2, eu-west-1, eu-central-1. All listed cases still Case Opened except prior west-2 G/VT 1024 Case Closed (`179041346400081`). No Approved/Denied. No GPU VMs running.

## Blocker
Cannot start GPU VMs until G/VT or P On-Demand vCPU quota > 0. Watch Service Quotas request history / support cases above.

## Quota filings update 2026-09-26 ~12:24 Europe/Warsaw
Small On-Demand G/VT 32 pending:
- us-west-2: `179041702400280`
- us-east-2: `179041728600007`
- eu-west-1: `179041759900212`
- eu-central-1: `179041780500011`
- ap-northeast-1 (Tokyo): `179041801500014`
- ap-southeast-1 (Singapore): `179041804600760`
- ap-northeast-2 (Seoul): `179041816100621`
Activate notes replied on: `179041702400280`, `179041759900212`, `179041728600007`, `179041353300510`, `179041340000396`, `179041351000024`
Still filing remaining commercial regions (Mumbai + others).

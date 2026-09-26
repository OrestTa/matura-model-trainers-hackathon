# Nebius expansion snapshot

Read from the authenticated Nebius console at approximately 18:44 UTC.

- Tenant: amber-centipede-tenant-6da.
- eu-north1 H100 allocation 11 / quota 32; H200 0 / 32; L40S 0 / 32.
- eu-north1 VM allocation 11 / quota 12. GPU quota is not the only constraint.
- Network SSD allocation 2.69 TiB / 6 TiB; disks 11 / 32.
- Billing balance $100.82; displayed consumption $47.18. Shared live workloads
  continue spending, so this is a timestamped balance, not guaranteed headroom.
- Existing workloads are not ours and must not be modified.

User authorized +50% experiment concurrency across Nebius and Modal. Reference
batch had four workers; target six useful workers. The Nebius deployment agent
owns the new isolated allocation. A single VM may host two experiment processes
where appropriate. Initial additional Nebius cost envelope $15, preserving at
least $50 shared balance, with explicit job/runtime caps and persisted outputs.
No deployment is claimed by this quota/balance snapshot; record instance/job IDs
and actual running status separately after verification.

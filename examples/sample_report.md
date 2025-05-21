🔧 Infrastructure Tuning Toolkit - Diagnostic Tool

🔧 Running Full SQL Server + VM Diagnostics
--------------------------------------------------

🖥️ Server CPU & Memory Specs:
 - Logical CPUs: 8
 - Hyperthread Ratio: 2
 - Physical Memory: 65536 MB
 - SQL Server Start Time: 2025-04-01 12:03:44
 - Virtual Machine Type: HYPERVISOR

✅ NUMA CPU distribution appears balanced.
⚠️ NUMA layout cannot be fully validated (parent_node_id missing).
❌ Unable to retrieve current maxDOP.
⚠️ Falling back to 1 NUMA node
🧠 Current maxDOP: None
✅ Recommended maxDOP: 8
📌 Reason: Single NUMA node - general best practice
✅ No CPU affinity mask detected. SQL sees all online CPUs.

🧩 CPU Socket Layout (Host OS View):
 - Sockets: 1
 - Physical Cores: 8
 - Logical Processors: 8
✅ Socket count is within SQL Server Standard Edition limits.

🧭 Host Environment: VMware
⚠️ Detected virtualized SQL Server environment.
📌 Ensure vNUMA is properly configured in the hypervisor.

💽 VM Hardware Configuration Check:
✅ Disks are using SCSI interface.
✅ VMXNET3 network adapter detected.

💾 Memory Grants (if any):
✅ No memory grant pressure detected.

✅ Diagnostics complete.

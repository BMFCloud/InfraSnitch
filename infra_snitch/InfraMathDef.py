# NUMA_Tuning_Toolkit
# This script is part of the NUMA Tuning Toolkit, a hybrid PowerShell and Python solution
# for optimizing NUMA (Non-Uniform Memory Access) configurations in Windows environments.
# The toolkit includes Python scripts for data processing and analysis, and PowerShell scripts
# for system configuration and reporting.
# The toolkit is designed to help system administrators and performance engineers
# identify and resolve NUMA-related performance issues in Windows systems.

# Created by: Brandon Fortunato
# Date: 2023-10-01

# Root repo structure for PowerShell + Python hybrid tooling

# Directory structure suggestion:
# /NUMA_Tuning_Toolkit
# ├── python/
# │   ├── __init__.py
# │   ├── db_connect.py
# │   ├── numa_checker.py
# │   ├── memory_validator.py
# │   ├── compression_recommender.py
# │   └── report_generator.py
# └── powershell/
#     ├── Get-NumaLayout.ps1
#     ├── Validate-Memory.ps1
#     ├── Recommend-Compression.ps1
#     └── Generate-Report.ps1

# --- python/db_connect.py ---
import pyodbc
import os
import logging
import platform
import subprocess
import argparse
import re
import sys
import getpass
import datetime

    
# --- python/numa_checker.py ---
class NumaChecker:
    
    def __init__(self, conn, output_func=print):
        self.conn = conn
        self.out = output_func
        self.out("🔧 Infrastructure Tuning Toolkit - Diagnostic Tool" )

    
    def get_scheduler_layout(self):
        query = """
        SELECT scheduler_id, cpu_id, is_online, status
        FROM sys.dm_os_schedulers
        WHERE scheduler_id < 255
        ORDER BY scheduler_id
        """
        return self.query_dict(query)

        
    
    
    def query_dict(self, sql):
        #"""Execute a SQL query and return the results as a list of dictionaries."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            columns = [column[0] for column in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            logging.info("Query executed successfully.")
            return results
        except pyodbc.Error as e:
            logging.error(f"Failed to execute query: {e}")
            raise
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            raise
        finally:
            cursor.close()
            logging.info("Cursor closed after executing query.")

   
    def get_memory_nodes(self):
        #"""Pulls memory allocation info from sys.dm_os_memory_nodes. Returns a list of dictionaries with per-node memory stats."""
        query = """
        SELECT memory_node_id,
           virtual_address_space_reserved_kb,
           virtual_address_space_committed_kb,
           locked_page_allocations_kb
        FROM sys.dm_os_memory_nodes
        
        WHERE memory_node_id != 64
        """
        return self.query_dict(query)
    
    
    def validate_numa_layout(self):
        #"""Validates NUMA scheduler layout:Warns if CPU counts are unbalanced across nodesWarns if any schedulers are offline"""
        schedulers = self.get_scheduler_layout()
        node_cpu_map = {}
        offline_schedulers = []

        for row in schedulers:
            cpu = row['cpu_id']
            is_online = row['is_online']
        if is_online == 0:
            offline_schedulers.append(cpu)


        # CPU count check
        cpu_counts = set(node_cpu_map.values())
        if len(cpu_counts) > 1:
            self.out("⚠️ NUMA nodes have unbalanced CPU counts:")
            for node, count in node_cpu_map.items():
                self.out(f" - Node {node}: {count} schedulers")
        else:
            self.out("✅ NUMA CPU distribution appears balanced.")

        # Offline schedulers
        if offline_schedulers:
            self.out(f"⚠️ Offline schedulers detected: {offline_schedulers}")
        else:
            self.out("✅ All schedulers are online.")

    
    
    def validate_memory_alignment(self):
        schedulers = self.get_scheduler_layout()
        memory_nodes = self.get_memory_nodes()

    # FALLBACK: Skip if node ID is missing from schedulers
        scheduler_node_ids = set()
        for row in schedulers:
            if 'parent_node_id' in row:
                scheduler_node_ids.add(row['parent_node_id'])

                memory_node_ids = set(row['memory_node_id'] for row in memory_nodes)

            if not scheduler_node_ids:
                self.out("⚠️ NUMA layout cannot be fully validated (parent_node_id missing).")
            return

        nodes_missing_memory = scheduler_node_ids - memory_node_ids
        memory_without_cpus = memory_node_ids - scheduler_node_ids

            
        if nodes_missing_memory:
                self.out("⚠️ NUMA nodes with schedulers but no memory assigned:")
        for node in sorted(nodes_missing_memory):
                self.out(f" - Node {node}")
        else:
                self.out("✅ All scheduler nodes have memory assigned.")

        if memory_without_cpus:
            self.out("⚠️ Memory nodes present without schedulers:")
        for node in sorted(memory_without_cpus):
            self.out(f" - Node {node}")
        else:
            self.out("✅ All memory nodes align with scheduler nodes.")

   
   
    def recommend_maxdop(self):
        #"""Recommends an appropriate maxDOP setting based on NUMA node count.Pulls current value from sp_configure and compares against guideline. """
        current_value = None
        try:
            cursor = self.conn.cursor()
            cursor.execute("SET IMPLICIT_TRANSACTIONS OFF;")  # prevents auto-transactions
            cursor.execute("EXEC sp_configure 'show advanced options', 1;")
            cursor.execute("RECONFIGURE;")
            self.conn.commit()

            #""""Fetch current maxDOP """"
            cursor.execute("EXEC sp_configure 'max degree of parallelism'")
            row = cursor.fetchone()
            current_value = row[1] if row else None
            cursor.close()

        except Exception as e:
            logging.error(f"Failed to fetch maxDOP: {e}")
            self.out("❌ Unable to retrieve current maxDOP.")
            current_value = None

        # Count NUMA nodes
        schedulers = self.get_scheduler_layout()
        # If parent_node_id is not available, fallback to 1 NUMA node
        if schedulers and 'parent_node_id' in schedulers[0]:
            numa_nodes = set(row['parent_node_id'] for row in schedulers if 'parent_node_id' in row)
            node_count = len(numa_nodes)
        else:
            node_count = 1  # Default fallback if unavailable
            self.out("⚠️ Falling back to 1 NUMA node (parent_node_id unavailable)")

        # Determine recommendation
        if node_count == 1:
            recommended = 8
            reason = "Single NUMA node - general best practice"
        else:
            recommended = node_count * 2
            reason = f"{node_count} NUMA nodes detected - scaling maxDOP accordingly"

        self.out(f"🧠 Current maxDOP: {current_value}")
        self.out(f"✅ Recommended maxDOP: {recommended}")
        self.out(f"📌 Reason: {reason}")
    
    def get_memory_config(self):
        memory_config = {}

        try:
            cursor = self.conn.cursor()

            # Disable implicit transactions to allow RECONFIGURE
            cursor.execute("SET IMPLICIT_TRANSACTIONS OFF;")
            cursor.execute("EXEC sp_configure 'show advanced options', 1;")
            cursor.execute("RECONFIGURE;")
            self.conn.commit()

            # Pull min/max SQL memory settings
            cursor.execute("EXEC sp_configure 'min server memory (MB)'")
            row = cursor.fetchone()
            memory_config['min_server_memory_mb'] = row[1] if row else None

            cursor.execute("EXEC sp_configure 'max server memory (MB)'")
            row = cursor.fetchone()
            memory_config['max_server_memory_mb'] = row[1] if row else None

            # Get physical RAM
            mem_query = "SELECT total_physical_memory_kb, available_physical_memory_kb FROM sys.dm_os_sys_memory"
            cursor.execute(mem_query)
            row = cursor.fetchone()
            if row:
                memory_config['total_physical_memory_mb'] = int(row[0] / 1024)
                memory_config['available_physical_memory_mb'] = int(row[1] / 1024)

            cursor.close()
            return memory_config

        except Exception as e:
            logging.error(f"Failed to fetch memory configuration: {e}")
            self.out("❌ Unable to retrieve memory configuration.")
            return memory_config


        

    def validate_memory_config(self):
        #"""Validates SQL Server memory config against system RAM.Flags:- Max memory > total physical memory- Min memory too low (e.g., under 25% of max)"""
        mem = self.get_memory_config()
        if not mem:
            return

        self.out("\n🔍 SQL Server Memory Configuration:")
        self.out(f" - Total Physical RAM: {mem['total_physical_memory_mb']} MB")
        self.out(f" - Available RAM: {mem['available_physical_memory_mb']} MB")
        self.out(f" - SQL Min Memory: {mem['min_server_memory_mb']} MB")
        self.out(f" - SQL Max Memory: {mem['max_server_memory_mb']} MB")

        total = mem['total_physical_memory_mb']
        min_mem = mem['min_server_memory_mb']
        max_mem = mem['max_server_memory_mb']

        if max_mem > total:
            self.out("⚠️ SQL Max Memory exceeds physical RAM. Risk of OS starvation.")
        else:
            self.out("✅ SQL Max Memory fits within physical RAM.")

        if min_mem < (max_mem * 0.25):
            self.out("⚠️ SQL Min Memory is set very low compared to Max. Could delay memory ramp-up.")
        else:
            self.out("✅ SQL Min/Max memory ratio looks reasonable.")

    def check_affinity_config(self):
        #"""Checks whether SQL Server is using CPU affinity masking.Warns if CPU usage is restricted or uneven across schedulers."""
        try:
            # Get scheduler info
            schedulers = self.get_scheduler_layout()

            # Check for any missing CPUs or partial core usage
            total_visible = [row for row in schedulers if row['status'] == 'VISIBLE ONLINE']
            all_online = [row for row in schedulers if row['is_online'] == 1]

            total_visible_cpu_ids = set(r['cpu_id'] for r in total_visible)
            total_online_cpu_ids = set(r['cpu_id'] for r in all_online)

            if total_visible_cpu_ids != total_online_cpu_ids:
                diff = total_online_cpu_ids - total_visible_cpu_ids
                self.out("⚠️ Affinity mask is likely applied. Some CPUs are online but not visible to SQL Server:")
                self.out(f"   Missing CPUs: {sorted(diff)}")
            else:
                self.out("✅ No CPU affinity mask detected. SQL sees all online CPUs.")

        except Exception as e:
            logging.error(f"Affinity config check failed: {e}")
            self.out("❌ Error checking affinity config.")
        
    def analyze_sql_workload(self, top_n: int = 5):
        #"""Analyzes SQL workload to identify top resource-consuming queries."""
        try:
            cursor = self.conn.cursor()

            self.out(f"\n🔍 Active SQL Requests (top {top_n}):")
            query = f"""
            SELECT 
                r.session_id,
                r.status,
                r.command,
                r.start_time,
                r.cpu_time,
                r.total_elapsed_time,
                t.text AS sql_text
            FROM sys.dm_exec_requests r
            CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t
            WHERE r.session_id > 50 -- Skip system sessions
            ORDER BY r.total_elapsed_time DESC
            """
            cursor.execute(query)
            rows = cursor.fetchmany(top_n)

            if not rows:
                self.out("✅ No active long-running queries.")
            else:
                for row in rows:
                    self.out(f"\n🧵 Session {row.session_id}")
                    self.out(f" - Status: {row.status}")
                    self.out(f" - Command: {row.command}")
                    self.out(f" - CPU Time: {row.cpu_time} ms")
                    self.out(f" - Elapsed Time: {row.total_elapsed_time} ms")
                    self.out(f" - SQL: {row.sql_text[:150]}...")
            self.out("\n💾 Memory Grants (if any):")
            mem_query ="""
            SELECT session_id, grant_time, requested_memory_kb, granted_memory_kb
            FROM sys.dm_exec_query_memory_grants
            WHERE granted_memory_kb < requested_memory_kb
            """

            cursor.execute(mem_query)
            mem_rows = cursor.fetchall()

            if not mem_rows:
                self.out("✅ No memory grant pressure detected.")
            else:
                for row in mem_rows:
                    self.out(f" - Session {row.session_id} waiting for memory: {row.requested_memory_kb} KB requested")

            cursor.close()
    
        except Exception as e:
            logging.error(f"SQL workload analysis failed: {e}")
            self.out("❌ Error analyzing SQL workload.")



    def detect_virtual_environment(self):
        #"""Detects if the SQL Server is running on a virtual machine.Flags known platforms like VMware, Hyper-V, KVM.Warns if vNUMA tuning should be evaluated."""
        try:
            # Use systeminfo to probe hardware model
            output = subprocess.getoutput("systeminfo")

            detected = "Bare Metal"
            flags = []

            if "VMware" in output:
                detected = "VMware"
            elif "Hyper-V" in output or "Virtual Machine" in output:
                detected = "Hyper-V"
            elif "KVM" in output or "QEMU" in output:
                detected = "KVM/QEMU"
            elif "Microsoft Corporation Virtual" in output:
                detected = "Azure (Hyper-V core)"

            self.out(f"\n🧭 Host Environment: {detected}")

            if detected != "Bare Metal":
                self.out("⚠️ Detected virtualized SQL Server environment.")
                self.out("📌 Ensure vNUMA is exposed and balanced properly in the hypervisor.")
                self.out("📌 Misaligned virtual sockets/cores can cause NUMA fragmentation.")

            return detected
        except Exception as e:
            logging.error(f"Virtual environment detection failed: {e}")
            self.out("❌ Error detecting virtual platform.")
            return "Unknown"
    
    def get_system_specs(self):
    #"""Reports core SQL-visible system specs: CPU count, logical processors, RAM size.Useful for understanding physical resource availability."""
        query = """
        SELECT 
            cpu_count,
            hyperthread_ratio,
            physical_memory_kb / 1024 AS physical_memory_mb,
            sqlserver_start_time,
            virtual_machine_type_desc
        FROM sys.dm_os_sys_info
        """
        try:
            data = self.query_dict(query)
            if not data:
                self.out("❌ Could not retrieve system specs.")
            else:
                row = data[0]
                self.out("\n🖥️ Server CPU & Memory Specs:")
                self.out(f" - Logical CPUs: {row['cpu_count']}")
                self.out(f" - Hyperthread Ratio: {row['hyperthread_ratio']}")
                self.out(f" - Physical Memory: {row['physical_memory_mb']} MB")
                self.out(f" - SQL Server Start Time: {row['sqlserver_start_time']}")
                self.out(f" - Virtual Machine Type: {row['virtual_machine_type_desc']}")
        except Exception as e:
            logging.error(f"System spec check failed: {e}")
            self.out("❌ Error retrieving system hardware configuration.")

    def check_socket_layout(self):
        #"""Detects CPU socket layout from the OS perspective.Flags if more than 2 sockets are visible (SQL Standard Edition limit)."""
        try:
            self.out("\n🧩 CPU Socket Layout (Host OS View):")
            output = subprocess.getoutput("wmic cpu get Name,NumberOfCores,NumberOfLogicalProcessors,SocketDesignation /format:list")

            # Get socket names (e.g., CPU0, CPU1, etc.)
            socket_matches = re.findall(r"SocketDesignation=(\S+)", output)
            socket_count = len(set(socket_matches))

        # Total physical cores
            core_matches = re.findall(r"NumberOfCores=(\d+)", output)
            total_cores = sum(map(int, core_matches))

        # Total logical processors (with hyperthreading)
            logical_matches = re.findall(r"NumberOfLogicalProcessors=(\d+)", output)
            total_logical = sum(map(int, logical_matches))

            self.out(f" - Sockets: {socket_count}")
            self.out(f" - Physical Cores: {total_cores}")
            self.out(f" - Logical Processors: {total_logical}")

            if socket_count > 2:
                self.out("⚠️ Detected more than 2 sockets.")
                self.out("❌ SQL Server Standard will only use 2 sockets regardless of core count.")
                self.out("📌 Recommendation: Reconfigure VM to use fewer sockets with more cores per socket (e.g., 1 socket × 8 cores).")
            else:
                self.out("✅ Socket count is within SQL Server Standard Edition limits.")

        except Exception as e:
            logging.error(f"Socket layout check failed: {e}")
            self.out("❌ Error retrieving socket layout from OS.")


    def check_virtual_hardware(self):
        #"""Verifies that disk controllers are SCSI and network adapters are VMXNET3.Helps ensure high-performance virtual hardware config."""
        self.out("\n💽 VM Hardware Configuration Check:")

        try:
            # --- Check Disk Controllers ---
            disk_output = subprocess.getoutput("wmic diskdrive get InterfaceType,Model")
            self.out("🔍 Disk Controllers:")
            if "SCSI" in disk_output:
                self.out("✅ Disks are using SCSI interface.")
            else:
                self.out("⚠️ Disks may not be using SCSI interface:")
                self.out(disk_output)

        # --- Check Network Adapters ---
            nic_output = subprocess.getoutput("wmic nic where 'AdapterTypeId=0 and NetEnabled=true' get Name,Manufacturer,AdapterType")
            self.out("\n🔍 Network Adapters:")
            if "VMXNET3" in nic_output.upper():
                self.out("✅ VMXNET3 network adapter detected.")
            else:
                self.out("⚠️ VMXNET3 not detected. Current adapters:")
                self.out(nic_output)

        except Exception as e:
            logging.error(f"Virtual hardware check failed: {e}")
            self.out("❌ Error retrieving virtual hardware info.")
        

    def run_all_diagnostics(self):
        #"""Runs the full system validation suite:NUMA, memory, licensing, workload, and VM hardware config."""
        self.out("\n🔧 Running Full SQL Server + VM Diagnostics\n" + "-"*50)

        self.get_system_specs()
        self.validate_numa_layout()
        self.validate_memory_alignment()
        self.recommend_maxdop()
        self.validate_memory_config()
        self.check_affinity_config()
        self.get_system_specs()
        self.check_socket_layout()
        self.detect_virtual_environment()
        self.check_virtual_hardware()
        self.analyze_sql_workload()

        self.out("\n✅ Diagnostics complete.")


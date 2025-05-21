InfraSnitch - SQL Server + VM NUMA Diagnostics Tool
----------------------------------------------------
This executable runs a series of infrastructure tuning checks against
a SQL Server instance and virtual environment.

🔐 Requirements:
 - ODBC Driver 17 or 18 for SQL Server (Microsoft)
 - SQL authentication access to the server

## 🛠 Usage

```bash
infra-snitch.exe --full                 # Run all diagnostics
infra-snitch.exe --memory              # Validate SQL memory configuration
infra-snitch.exe --maxdop              # Analyze max degree of parallelism
infra-snitch.exe --affinity            # Check CPU affinity settings
infra-snitch.exe --workload            # Show current SQL workload
infra-snitch.exe --hardware            # Verify VM hardware config
infra-snitch.exe --output myserver     # Set custom report filename prefix
infra-snitch.exe --dry-run             # Run tool with no SQL connection (simulation mode)
infra-snitch.exe --verbose             # Enable detailed console output
infra-snitch.exe --debug               # Show raw error messages and tracebacks


📄 Output:
 - Markdown report: numa_diagnostics_<servername>.md
 - JSON report:     numa_diagnostics_<servername>.json
 - Console summary: Shows count of ✅ passes, ⚠️ warnings, and ❌ errors

💡 You can customize the filename prefix using --output:
    e.g., --output prod-sql creates:
    - numa_diagnostics_prod-sql.md
    - numa_diagnostics_prod-sql.json

📥 Logs and reports are stored in the same directory as the executable.



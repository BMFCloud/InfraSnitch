import argparse
import re
from report_logger import ReportLogger
from db_connect import get_connection
from InfraMathDef import NumaChecker

def main():
    parser = argparse.ArgumentParser(description="NUMA Tuning Toolkit CLI")
    parser.add_argument('--full', action='store_true', help="Run full diagnostics")
    parser.add_argument('--maxdop', action='store_true', help="Recommend maxDOP setting")
    parser.add_argument('--memory', action='store_true', help="Validate SQL memory settings")
    parser.add_argument('--affinity', action='store_true', help="Check CPU affinity config")
    parser.add_argument('--workload', action='store_true', help="Analyze SQL workload")
    parser.add_argument('--hardware', action='store_true', help="Check VM hardware")
    parser.add_argument('--output', type=str, help="Set custom output filename prefix (e.g., 'prod-sql01')")
    parser.add_argument('--dry-run', action='store_true', help="Simulate diagnostics without connecting to SQL Server")
    parser.add_argument('--verbose', action='store_true', help="Enable verbose output")
    parser.add_argument('--debug', action='store_true', help="Enable debug output")

    args = parser.parse_args()

    if args.dry_run:
        server_name = "dry_run"
        logger = ReportLogger()
        logger.write("🧪 Dry Run Mode: Skipping SQL Server connection and database diagnostics.")
        checker = None
    else:
        conn, server_name = get_connection()
        logger = ReportLogger()
        checker = NumaChecker(conn, output_func=logger.write)


    if not args.dry_run:
        if args.full:
            checker.run_all_diagnostics()
        if args.maxdop:
            checker.recommend_maxdop()
        if args.memory:
            checker.validate_memory_config()
        if args.affinity:
            checker.check_affinity_config()
        if args.workload:
            checker.analyze_sql_workload()
        if args.hardware:
            checker.check_virtual_hardware()


    # Determine base filename
    safe_name = re.sub(r'[^A-Za-z0-9_\-]', '_', args.output) if args.output else re.sub(r'[^A-Za-z0-9_\-]', '_', server_name)

    logger.export(f"numa_diagnostics_{safe_name}.md")
    logger.export_json(f"numa_diagnostics_{safe_name}.json")
    logger.print_summary()


if __name__ == "__main__":
    main()

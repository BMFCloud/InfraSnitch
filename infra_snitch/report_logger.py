from io import StringIO
import json

class ReportLogger:
    def __init__(self):
        self.console = print
        self.buffer = StringIO()

    def write(self, msg):
        self.console(msg)
        self.buffer.write(msg + "\n")

    def export(self, filename="numa_diagnostics.md"):
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.buffer.getvalue())
        print(f"\n📄 Markdown report saved to: {filename}")

    def export_json(self, filename="numa_diagnostics.json"):
        #"""Export the report as a JSON file with a list of log lines."""
        lines = self.buffer.getvalue().splitlines()
        report = {"report": lines}
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 JSON report saved to: {filename}")

    def print_summary(self):
        #"""Prints a basic summary of how many checks passed or raised warnings/errors."""
        lines = self.buffer.getvalue().splitlines()
        warnings = [line for line in lines if "⚠️" in line or "❌" in line]
        successes = [line for line in lines if "✅" in line]

        print("\n📋 Summary:")
        print(f" - ✅ Successes: {len(successes)}")
        print(f" - ⚠️ Warnings: {len(warnings)}")
        if warnings:
            print(" - Highlighted Issues:")
            for line in warnings[:5]:
                print(f"   {line}")
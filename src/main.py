
import subprocess
import sys


def run_step(description, module):
    print("\n" + "=" * 60, flush=True)
    print(description, flush=True)
    print("=" * 60, flush=True)

    result = subprocess.run(
        [sys.executable, "-m", module],
        check=False,
    )

    if result.returncode != 0:
        print(
            "\nFAILED: {} (exit code {})".format(
                module, result.returncode
            ),
            flush=True,
        )
        return False

    print("PASSED: {}".format(module), flush=True)
    return True


def main():
    steps = [
        ("Validate database and data quality", "src.validate_data"),
        ("Validate assignment workflows", "src.validate_workflows"),
        ("Detect the four anomaly scenarios", "src.detect_anomalies"),
        ("Export CSV, JSON, and SQL deliverables", "src.export_data"),
    ]

    for description, module in steps:
        if not run_step(description, module):
            sys.exit(1)

    print("\nAll project pipeline steps completed successfully.")


if __name__ == "__main__":
    main()

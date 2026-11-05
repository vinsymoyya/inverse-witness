import argparse
import json
from pathlib import Path

from .exact import verify


def main():
    parser = argparse.ArgumentParser(description="Inverse Witness research CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("verify", help="Check a certificate without NumPy or SciPy")
    check.add_argument("file", type=Path)
    check.add_argument("--max-gap", default=None, help="Exact rational maximum gap")
    demo = sub.add_parser("demo", help="Generate a physics ambiguity and measurement-choice example")
    demo.add_argument("--output", type=Path, default=Path("results/demo"))
    acquisition = sub.add_parser("acquisition", help="Replay measured thermal acquisitions and injected failures")
    acquisition.add_argument("--output", type=Path, required=True)
    acquisition.add_argument("--data", type=Path, default=Path("data/tclab_apmonitor"))
    args = parser.parse_args()
    if args.command == "verify":
        print(json.dumps(verify(json.loads(args.file.read_text(encoding="utf-8")), args.max_gap), indent=2))
    elif args.command == "demo":
        from .experiment import run_demo
        print(json.dumps(run_demo(args.output), indent=2))
    else:
        from .acquisition_experiment import run_acquisition
        print(json.dumps(run_acquisition(args.output, args.data), indent=2))


if __name__ == "__main__":
    main()

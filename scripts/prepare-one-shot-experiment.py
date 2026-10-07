"""Build/assess a zero-network preparation manifest; never create identity or credentials."""

import argparse
import json
import time
from pathlib import Path

from pydantic import ValidationError

from sim2act.errors import DomainError
from sim2act.one_shot_preparation import assess, prepare


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--intake", type=Path)
    args = parser.parse_args()
    value = prepare(Path(__file__).resolve().parents[1])
    try:
        intake = json.loads(args.intake.read_text()) if args.intake else value["intake_template"]
        result = {"preparation": value, "assessment": assess(value, intake, now=time.time())}
    except (ValueError, UnicodeDecodeError, ValidationError, DomainError):
        # Never echo an invalid intake field or a credential accidentally supplied there.
        parser.error("Invalid preparation metadata; credentials are not accepted")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as output:
        output.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "state": result["assessment"]["state"],
                "live_ready": False,
                "effective_request_budget": 0,
                "network_requests": 0,
            }
        )
    )


if __name__ == "__main__":
    main()

import argparse
import json
import secrets

from .config import Settings
from .contracts import ActionSpec, AppManifest, Approval, GoalSpec, Grant, Operation, Run
from .db import Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate", "init-user", "schemas"])
    parser.add_argument("--name", default="Local user")
    args = parser.parse_args()
    if args.command == "schemas":
        from pathlib import Path

        path = Path("schemas")
        path.mkdir(exist_ok=True)
        models: list[
            type[GoalSpec]
            | type[ActionSpec]
            | type[AppManifest]
            | type[Run]
            | type[Operation]
            | type[Grant]
            | type[Approval]
        ] = [GoalSpec, ActionSpec, AppManifest, Run, Operation, Grant, Approval]
        for cls in models:
            (path / (cls.__name__ + ".json")).write_text(
                json.dumps(cls.model_json_schema(), indent=2) + "\n"
            )
        return
    s = Settings.from_env()
    store = Store(s.database_url)
    if args.command == "migrate":
        store.initialize(s.quota_subject)
        print("Schema initialized; keep migration role separate from runtime role.")
    else:
        token = secrets.token_urlsafe(32)
        store.user(args.name, token)
        print("Local UI bearer token (shown once; store privately, never commit): " + token)


if __name__ == "__main__":
    main()

import argparse
import json
import secrets

from .config import Settings
from .contracts import ActionSpec, AppManifest, Approval, GoalSpec, Grant, Operation, Run
from .db import Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate", "init-user", "schemas", "probe", "synthetic-workspace"])
    parser.add_argument("--name", default="Local user")
    parser.add_argument("--output")
    parser.add_argument("--data-dir")
    parser.add_argument("--new", action="store_true")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--control-stdin", action="store_true", help="Private desktop-owned synthetic shutdown pipe")
    args = parser.parse_args()
    if args.command != "synthetic-workspace" and (args.data_dir or args.new or args.port != 0 or args.control_stdin):
        parser.error("--data-dir, --new, --port and --control-stdin belong to synthetic-workspace only")
    if args.command == "synthetic-workspace":
        from .synthetic_workspace import WorkspaceError, serve

        if not args.data_dir:
            parser.error("synthetic-workspace requires an explicit --data-dir")
        try:
            serve(args.data_dir, new=args.new, port=args.port, control_stdin=args.control_stdin)
        except WorkspaceError as error:
            parser.exit(1, "Synthetic workspace stopped; existing data preserved: " + str(error) + "\n")
        except Exception:
            parser.exit(1, "Synthetic workspace failed; data preserved; check local prerequisites.\n")
        return
    if args.command == "probe":
        from pathlib import Path

        from .probe import offline_probe

        report = json.dumps(offline_probe(), ensure_ascii=False, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(report, encoding="utf-8")
        else:
            print(report)
        return
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

"""Original explicit launch configuration and approval prechecks, shared by CLI/desktop.

No credential discovery, migrations, grants or synthetic production authority.
"""
import json
import os
import re
from pathlib import Path


def import_config(path, *, base_dir=None):
    """Explicit private file only; never discover, execute or print its values."""
    path = Path(path)
    if not path.is_absolute():
        path = Path.cwd() / path if base_dir is None else Path(base_dir) / path
    try:
        with path.open(encoding="utf-8-sig") as stream:
            content = stream.read(65537)
        if len(content) > 65536 or "\0" in content:
            raise ValueError
        values = {}
        for line in content.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            match = re.fullmatch(r"(SIM2ACT_[A-Z_]+|INTERN_API_TOKEN)=(.*)", line)
            if match is None or match[1] in values:
                raise ValueError
            if len((match[1] + "=" + match[2]).encode("utf-16-le")) // 2 > 32760:
                raise ValueError
            values[match[1]] = match[2]
    except (OSError, UnicodeError, ValueError):
        raise ValueError(
            "Selected configuration is missing, duplicated or malformed; edit it privately."
        ) from None
    os.environ.update(values)


def production_selection(path):
    """Five original selectors only; neither a credential nor an approval."""
    from sim2act.production_evidence import ACCOUNT_ID

    try:
        with Path(path).open(encoding="utf-8-sig") as stream:
            value = stream.read(4097)
        if len(value) > 4096:
            raise ValueError

        def unique(pairs):
            data = {}
            for key, item in pairs:
                if key in data:
                    raise ValueError
                data[key] = item
            return data

        value = json.loads(value, object_pairs_hook=unique)
        patterns = dict(
            user=r"user_[a-f0-9]{32}",
            project=r"proj_[a-f0-9]{32}",
            trial=r"[A-Za-z0-9_-]{1,100}",
            approval=r"[A-Za-z0-9_-]{1,100}",
            account=re.escape(ACCOUNT_ID),
        )
        if (
            type(value) is not dict
            or set(value) != set(patterns)
            or any(
                type(value[k]) is not str or re.fullmatch(pattern, value[k]) is None
                for k, pattern in patterns.items()
            )
        ):
            raise ValueError
    except (OSError, UnicodeError, ValueError, TypeError):
        raise ValueError(
            "Select an existing five-field Intern trial selection; no credentials or extra fields."
        ) from None
    return value


def selection_worker_arguments(selection):
    return [
        part for name, value in selection.items() for part in ("--spec-production-" + name, value)
    ]


def check_selection(store, settings, selection):
    from sqlalchemy import select

    from sim2act.db import quotas
    from sim2act.spec_production import install

    # Original contract/approval/account/software/permission checks; this
    # constructs a Worker but never claims a Run or sends a model request.
    install(
        store,
        settings,
        user=selection["user"],
        project_id=selection["project"],
        trial_key=selection["trial"],
        approval_key=selection["approval"],
        account_id=selection["account"],
    )
    with store.engine.connect() as connection:
        exists = connection.execute(
            select(quotas.c.subject).where(quotas.c.subject == settings.quota_subject)
        ).first()
    if exists is None:
        raise ValueError("QUOTA_SUBJECT_NOT_INITIALIZED")


def validation_store(settings):
    """Bound only the explicit diagnostic/prelaunch connection, not Run leases."""
    from sqlalchemy.engine import make_url

    from sim2act.db import Store

    url = make_url(settings.database_url)
    if url.password == "LOCAL_PASSWORD":
        raise ValueError("Template database credential must be replaced privately")
    options = url.query.get("options", "")
    if type(options) is not str:
        raise ValueError("Unsupported diagnostic connection options")
    url = url.update_query_dict(
        dict(
            connect_timeout="5", options=options + " -c statement_timeout=5000 -c lock_timeout=1000"
        )
    )
    return Store(url.render_as_string(hide_password=False))



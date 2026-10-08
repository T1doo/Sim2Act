"""Immutable archived Report presentation previews on the existing graph ledger.

The canonical graph and execution candidate remain unchanged. A successful text
readback never completes the original conservative PROJECT revalidation plan.
"""


from fastapi import Depends
from pydantic import Field
from sqlalchemy import select

from . import delivery_graph as core
from . import delivery_graph_apps as graph
from . import report_manifest_apps as report
from .column_patches import CheckInput, read_pair, require_capacity
from .contracts import Strict, View, validate_value
from .db import delivery_graph_requests as requests
from .db import fingerprint
from .errors import DomainError

KIND = "report_presentation"
CHECK = "report_presentation_check"
KEY = r"^[A-Za-z0-9_-]{1,100}$"


class Definition(Strict):
    expected_candidate_fingerprint: str = Field(pattern=graph.HASH)
    expected_graph_fingerprint: str = Field(pattern=graph.HASH)
    plan_key: str = Field(pattern=KEY)
    expected_plan_fingerprint: str = Field(pattern=graph.HASH)
    run_id: str = Field(pattern=report.RUN)
    expected_run_version: int = Field(ge=1, strict=True)
    expected_run_fence: int = Field(ge=0, strict=True)
    expected_result_fingerprint: str = Field(pattern=graph.HASH)
    view: View
    request_key: str = Field(pattern=KEY)


def flags():
    return dict(kind="ARCHIVED_RESULT_PRESENTATION_ONLY", actual_material_verification="PENDING",
                semantic_status="UNKNOWN", owner_acceptance="PENDING",
                overall_run_acceptance="NOT_ACCEPTED", formal_publication_enabled=False,
                canonical_patch_executed=False, business_writes=0, model_requests=0)


def scope(store, c, user, pid, aid, body, limits):
    saved = graph.current(store, c, user, pid, aid, limits)
    draft, manifest, _, _ = report.load(store, c, user, aid, limits, pid)
    if (draft["fingerprint"] != body.expected_candidate_fingerprint
            or saved["graph"]["graph_fingerprint"] != body.expected_graph_fingerprint):
        graph.conflict("Presentation baseline changed")
    slots = [n for n in saved["graph"]["nodes"] if n["kind"] == "VIEW"]
    if len(slots) != 1 or slots[0]["definition"] != {"component_ref": "text", "output_field": "decision"}:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Only the original decision text slot exists")
    slot = slots[0]
    if body.view.model_dump() != {"component_ref": "text", "output_field": "explanation"}:
        raise DomainError("UNSUPPORTED_CAPABILITY", "Only text decision to explanation is supported")
    for field in ("decision", "explanation"):
        producer = manifest.outputs.get(field)
        if (producer is None or producer.source != "step" or producer.ref != "report"
                or producer.field != field
                or manifest.output_schema["properties"].get(field, {}).get("type") != "string"):
            raise DomainError("UNSUPPORTED_CAPABILITY", "Declared string producers required")
    row = graph.lookup(c, user, aid, "plan", body.plan_key)
    if not row:
        graph.conflict("An exact original impact plan is required")
    plan_body, outer = graph.checked_request(row)
    graph.validate_plan_seal(c, user, aid, body.plan_key, row)
    graph.verify_outer(outer)
    change = dict(node_id=slot["id"], expected_revision=slot["revision"],
                  expected_content_fingerprint=slot["content_fingerprint"])
    if (plan_body.expected_graph_fingerprint != body.expected_graph_fingerprint
            or fingerprint([x.model_dump() for x in plan_body.changes]) != fingerprint([change])
            or outer["native_outer_fingerprint"] != body.expected_plan_fingerprint):
        graph.conflict("Impact plan does not select the exact original VIEW slot")
    fresh = core.plan_change(saved["graph"], body.expected_graph_fingerprint,
                             dict(project_id=pid, app_id=aid, request_key=body.plan_key,
                                  changes=[change]), saved["context"], outer["receipt"])
    _, expansion = graph.expansion(store, c, user, pid, aid, fresh, limits, body.plan_key)
    graph.verify_jobs(c, user, aid, body.plan_key, outer["scope_jobs"])
    if fingerprint(expansion) != fingerprint(outer["scope_expansion"]):
        graph.conflict("Project membership, sources, authority or locks changed")
    # No scope narrowing: the original PROJECT uncertainty and omissions survive.
    items = report.records(store, c, user, draft, manifest)
    selected = next((item for item in items if item["run"]["run_id"] == body.run_id), None)
    if selected is None:
        raise DomainError("PERMISSION_DENIED")
    run = selected["run"]
    if (run["version"] != body.expected_run_version or run["fence"] != body.expected_run_fence
            or run["result_fingerprint"] != body.expected_result_fingerprint):
        graph.conflict("Confirm the exact archived Report result version")
    if run["status"] != "WAITING_APPROVAL" or not run["result"]:
        raise DomainError("VERIFICATION_FAILED", "A completed unaccepted archived Report is required")
    output = run["result"]["protocol_result"]["evidence"]["output"]
    validate_value(manifest.output_schema, output, "archived_report_output")
    return saved, slot, outer, output


def build(store, c, user, pid, aid, body, limits):
    saved, slot, outer, _ = scope(store, c, user, pid, aid, body, limits)
    definition = dict(slot_id=slot["id"], slot_key=slot["key"],
                      baseline_revision=slot["revision"], baseline_view=slot["definition"],
                      presentation_revision=slot["revision"] + 1, view=body.view.model_dump())
    answer = dict(namespace="report-presentation.v1", project_id=pid, app_id=aid,
                  request_key=body.request_key, definition=definition,
                  candidate_fingerprint=body.expected_candidate_fingerprint,
                  baseline_graph_fingerprint=body.expected_graph_fingerprint,
                  authorization_fingerprint=saved["authorization_fingerprint"],
                  result_binding=dict(run_id=body.run_id, version=body.expected_run_version,
                                      fence=body.expected_run_fence,
                                      result_fingerprint=body.expected_result_fingerprint),
                  impact_plan=outer, preserved_objects=saved["graph"]["nodes"],
                  preserved_edges=saved["graph"]["edges"], state="PRESENTATION_DRAFT",
                  project_revalidation_status=outer["scope_expansion"]["status"],
                  **flags())
    answer["patch_fingerprint"] = fingerprint(answer)
    return answer


def load(store, c, user, pid, aid, key, limits):
    # Current authorization precedes any protected receipt access.
    graph.current(store, c, user, pid, aid, limits)
    body, answer = read_pair(c, user, aid, KIND, key, Definition)
    if fingerprint(build(store, c, user, pid, aid, body, limits)) != fingerprint(answer):
        graph.conflict("Archived presentation binding changed")
    return body, answer


@graph.controlled
def propose(store, user, pid, aid, body, limits):
    with store.tx() as c:
        answer = build(store, c, user, pid, aid, body, limits)
        if graph.lookup(c, user, aid, KIND, body.request_key):
            old, previous = load(store, c, user, pid, aid, body.request_key, limits)
            if fingerprint(old.model_dump()) != fingerprint(body.model_dump()):
                graph.conflict("Presentation request key changed")
            return {**previous, "cached": True}
        require_capacity(c, user, aid, KIND)
        graph.remember(c, user, aid, KIND, body.request_key, body, answer)
        graph.remember(c, user, aid, KIND + "_seal", body.request_key, body, answer)
        return {**answer, "cached": False}


def readback(store, c, user, pid, aid, body, patch, check_body, limits):
    _, slot, _, output = scope(store, c, user, pid, aid, body, limits)
    if check_body.expected_patch_fingerprint != patch["patch_fingerprint"]:
        graph.conflict("Confirm the exact saved presentation version")
    answer = dict(namespace="report-presentation-readback.v1", project_id=pid, app_id=aid,
                  request_key=check_body.request_key, patch_fingerprint=patch["patch_fingerprint"],
                  result_binding=patch["result_binding"], slot_id=slot["id"],
                  baseline_text=output["decision"], text=output["explanation"],
                  view=body.view.model_dump(), display_readback_status="PASS",
                  project_revalidation_status=patch["project_revalidation_status"],
                  state="PRESENTATION_PREVIEW_ONLY", **flags())
    answer["check_fingerprint"] = fingerprint(answer)
    return answer


@graph.controlled
def check(store, user, pid, aid, key, body, limits):
    with store.tx() as c:
        definition, patch = load(store, c, user, pid, aid, key, limits)
        answer = readback(store, c, user, pid, aid, definition, patch, body, limits)
        if graph.lookup(c, user, aid, CHECK, body.request_key):
            old, previous = read_pair(c, user, aid, CHECK, body.request_key, CheckInput)
            if (fingerprint(old.model_dump()) != fingerprint(body.model_dump())
                    or fingerprint(previous) != fingerprint(answer)):
                graph.conflict("Presentation check request or current readback changed")
            return {**previous, "cached": True}
        require_capacity(c, user, aid, CHECK)
        graph.remember(c, user, aid, CHECK, body.request_key, body, answer)
        graph.remember(c, user, aid, CHECK + "_seal", body.request_key, body, answer)
        return {**answer, "cached": False}


@graph.controlled
def history(store, user, pid, aid, limits):
    with store.tx() as c:
        graph.current(store, c, user, pid, aid, limits)
        report.load(store, c, user, aid, limits, pid)
        def keys(kind):
            return c.execute(select(requests.c.request_key).where(
                requests.c.app_id == aid, requests.c.principal_id == user,
                requests.c.kind == kind).order_by(requests.c.request_key)).scalars().all()
        items = []
        checks = [read_pair(c, user, aid, CHECK, key, CheckInput) for key in keys(CHECK)]
        for key in keys(KIND):
            definition, patch = load(store, c, user, pid, aid, key, limits)
            matching = []
            for body, answer in checks:
                if answer["patch_fingerprint"] == patch["patch_fingerprint"]:
                    if fingerprint(readback(store, c, user, pid, aid, definition, patch, body, limits)) != fingerprint(answer):
                        graph.conflict("Saved presentation readback changed")
                    matching.append(answer)
            items.append(dict(patch=patch, checks=matching))
        if any(not any(item["patch"]["patch_fingerprint"] == answer["patch_fingerprint"] for item in items)
               for _, answer in checks):
            graph.conflict("Orphaned presentation check")
        return dict(namespace="report-presentation-history.v1", project_id=pid, app_id=aid,
                    items=items, **flags())


def mount(app, store, identity, limits, settings):
    dependency = Depends(identity)
    base = "/api/projects/{pid}/apps/{aid}/delivery-graph/report-presentations"

    def offline():
        if settings.mode != "mock":
            raise DomainError("PERMISSION_DENIED", "Only offline archived presentation previews exist")

    @app.post(base, status_code=201)
    def define(pid: str, aid: str, body: Definition, user=dependency):
        offline()
        return propose(store, user, pid, aid, body, limits)

    @app.post(base + "/{key}/checks", status_code=201)
    def confirm(pid: str, aid: str, key: str, body: CheckInput, user=dependency):
        offline()
        return check(store, user, pid, aid, key, body, limits)

    @app.get(base)
    def read(pid: str, aid: str, user=dependency):
        return history(store, user, pid, aid, limits)

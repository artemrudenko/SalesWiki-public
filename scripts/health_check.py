#!/usr/bin/env python3
"""SalesWiki structural health checks.

This script intentionally uses only the Python standard library so it can run
in a plain Obsidian vault checkout.
"""

from __future__ import annotations

import re
import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ENTITY_TEMPLATE_GLOB = "wiki/entities/*/_template.md"

REQUIRED_FRONTMATTER_KEYS = {
    "type",
    "entity_id",
    "template_version",
    "created",
    "updated",
    "access",
    "profile_lock",
    "deletion_status",
    "tags",
}

GLOBAL_REQUIRED_SECTIONS = {
    "Controlled Profile",
    "Linked Entities",
    "Evidence",
    "Review Needed",
    "Change History",
}

REQUIRED_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    ".claude/skills/saleswiki-obsidian/SKILL.md",
    ".claude/skills/saleswiki-lead-scoring/SKILL.md",
    ".claude/skills/saleswiki-scoring-configurator/SKILL.md",
    ".claude/agents/research-orchestrator.md",
    ".claude/agents/connector-sync-planner.md",
    ".claude/agents/privacy-redaction-reviewer.md",
    ".claude/agents/event-research.md",
    "README.md",
    "reports/README.md",
    "docs/AGENT_PORTABILITY.en.md",
    "docs/SETUP.en.md",
    "wiki/index.md",
    "wiki/log.md",
    "schemas/property-vocabularies.json",
    "schemas/scoring-models.json",
    "schemas/connector-contracts.json",
    "config/runtime.example.toml",
    "schemas/agent-routing.json",
    "schemas/event-research-profile.json",
    "scripts/audit_external_vault.py",
    "scripts/build_dashboard_snapshots.py",
    "scripts/build_indexes.py",
    "scripts/generate_demo_digests.py",
    "scripts/generate_demo_vault.py",
    "scripts/refresh.py",
    "scripts/import_external_vault.py",
    "wiki/processes/access-and-redaction-policy.md",
    "wiki/processes/card-taxonomy.md",
    "wiki/processes/data-engineering-contract.md",
    "wiki/processes/dashboard-contract.md",
    "wiki/processes/demo-vault.md",
    "wiki/processes/pilot-data-contract.md",
    "wiki/processes/connector-contracts.md",
    "wiki/processes/agent-orchestration.md",
    "wiki/processes/browser-research-method-comparison.md",
    "wiki/processes/event-research-profile.md",
    "wiki/processes/event-roi-action-loop.md",
    "wiki/processes/external-vault-import.md",
    "wiki/processes/file-drop-ingest-contract.md",
    "wiki/processes/global-property-dictionary.md",
    "wiki/processes/property-vocabularies.md",
    "wiki/processes/freshness-and-decay.md",
    "wiki/processes/google-meet-participant-matching.md",
    "wiki/processes/marketing-attribution-and-content-workflow.md",
    "wiki/processes/private-case-promotion-pipeline.md",
    "wiki/processes/report-templates.md",
    "wiki/processes/relationship-model.md",
    "wiki/processes/reminder-and-task-workflow.md",
    "wiki/processes/sales-marketing-research-framework.md",
    "wiki/processes/score-calibration.md",
    "wiki/processes/obsidian-skills.md",
    "wiki/processes/permission-boundary-blueprint.md",
    "wiki/processes/source-governance.md",
    "wiki/processes/hubspot-field-matrix.md",
    "wiki/processes/hubspot-lifecycle-mapping.md",
    "wiki/processes/scoring-models-v1.md",
    "wiki/processes/scoring-configuration.md",
    "tracking/processed-sources.md",
    "tracking/dedupe-register.md",
    "tracking/corroboration-register.md",
    "state/access-review.md",
    "state/connector-review.md",
    "state/hubspot-writeback-proposals.md",
    "state/ingest-runs.md",
    "state/index-status.md",
    "state/score-feedback.md",
    "state/scoring-change-requests.md",
    "state/system-health.md",
]

REQUIRED_RAW_DIRS = [
    "raw/assets",
    "raw/calls",
    "raw/campaigns",
    "raw/companies",
    "raw/crm",
    "raw/deals",
    "raw/events",
    "raw/imports",
    "raw/kb",
    "raw/leads",
    "raw/meetings",
    "raw/news",
    "raw/people",
    "raw/private-cases",
    "raw/research",
]

REQUIRED_DASHBOARDS = [
    "dashboards/sales-today.base",
    "dashboards/lead-priority.base",
    "dashboards/deal-risk.base",
    "dashboards/review-queue.base",
    "dashboards/monitoring.base",
    "dashboards/marketing-insights.base",
    "dashboards/data-quality.base",
]

def load_vocabularies() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    schema = json.loads((ROOT / "schemas/property-vocabularies.json").read_text(encoding="utf-8"))
    property_values = {key: set(values) for key, values in schema["property_allowed_values"].items()}
    card_statuses = {key: set(values) for key, values in schema["card_status_allowed"].items()}
    return property_values, card_statuses


PROPERTY_ALLOWED_VALUES, CARD_STATUS_ALLOWED = load_vocabularies()


def load_json(rel: str) -> dict[str, object]:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

DATE_KEYS = {
    "created",
    "updated",
    "last_reviewed",
    "last_checked",
    "next_check",
    "scored_at",
    "next_review",
    "date",
    "date_published",
    "date_collected",
    "crm_last_synced",
    "close_date",
    "last_touched",
    "last_updated",
}


@dataclass
class Finding:
    severity: str
    path: str
    message: str

    def render(self) -> str:
        return f"[{self.severity}] {self.path}: {self.message}"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(text: str) -> dict[str, str]:
    # Tolerate a leading UTF-8 BOM and CRLF line endings (Windows authoring) so a
    # `dataset: pilot` card cannot slip past the boundary check on encoding alone.
    text = text.lstrip("﻿").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    return data


def headings(text: str) -> set[str]:
    result: set[str] = set()
    for match in re.finditer(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE):
        result.add(match.group(1).strip())
    return result


def check_required_files(findings: list[Finding]) -> None:
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            findings.append(Finding("ERROR", rel, "required file is missing"))


def check_raw_dirs(findings: list[Finding]) -> None:
    for rel in REQUIRED_RAW_DIRS:
        path = ROOT / rel
        if not path.is_dir():
            findings.append(Finding("ERROR", rel, "required raw directory is missing"))


def check_dashboards(findings: list[Finding]) -> None:
    for rel in REQUIRED_DASHBOARDS:
        path = ROOT / rel
        if not path.exists():
            findings.append(Finding("ERROR", rel, "required Obsidian Bases dashboard is missing"))
            continue

        text = read(path)
        if "\t" in text:
            findings.append(Finding("ERROR", rel, "dashboard contains tab characters; use spaces for YAML-like structure"))
        for marker in ("filters:", "properties:", "views:"):
            if marker not in text:
                findings.append(Finding("ERROR", rel, f"dashboard missing `{marker}` block"))


def check_entity_templates(findings: list[Finding]) -> None:
    templates = sorted(ROOT.glob(ENTITY_TEMPLATE_GLOB))
    if not templates:
        findings.append(Finding("ERROR", ENTITY_TEMPLATE_GLOB, "no entity templates found"))
        return

    seen_types: dict[str, str] = {}
    for path in templates:
        rel = path.relative_to(ROOT).as_posix()
        text = read(path)
        fm = frontmatter(text)
        if not fm:
            findings.append(Finding("ERROR", rel, "missing YAML frontmatter"))
            continue

        for key in sorted(REQUIRED_FRONTMATTER_KEYS):
            if key not in fm:
                findings.append(Finding("ERROR", rel, f"missing frontmatter key `{key}`"))

        card_type = fm.get("type")
        if card_type:
            if card_type in seen_types:
                findings.append(
                    Finding("ERROR", rel, f"duplicate type `{card_type}` also in {seen_types[card_type]}")
                )
            seen_types[card_type] = rel

        present = headings(text)
        for section in sorted(GLOBAL_REQUIRED_SECTIONS):
            if section not in present:
                findings.append(Finding("ERROR", rel, f"missing required section `## {section}`"))


def check_frontmatter_allowed_values(findings: list[Finding]) -> None:
    """Validate simple scalar enum values in templates and instantiated cards."""
    for path in sorted(ROOT.glob("wiki/entities/*/*.md")):
        rel = path.relative_to(ROOT).as_posix()
        fm = frontmatter(read(path))
        for key, allowed in PROPERTY_ALLOWED_VALUES.items():
            if key not in fm:
                continue
            value = fm[key].strip().strip('"').strip("'")
            if not value or value.startswith("["):
                continue
            if value not in allowed:
                findings.append(
                    Finding("ERROR", rel, f"`{key}` value `{value}` is not allowed; expected one of {sorted(allowed)}")
                )
        card_type = fm.get("type", "")
        status = fm.get("status", "")
        if status and card_type in CARD_STATUS_ALLOWED and status not in CARD_STATUS_ALLOWED[card_type]:
            findings.append(
                Finding("ERROR", rel, f"`status` value `{status}` is not allowed for `{card_type}`; expected one of {sorted(CARD_STATUS_ALLOWED[card_type])}")
            )


def check_real_card_data_quality(findings: list[Finding]) -> None:
    """Validate instantiated card IDs, dates, numeric ranges and obvious duplicates."""
    seen_ids: dict[str, str] = {}
    seen_names: dict[tuple[str, str], str] = {}
    for path in sorted(ROOT.glob("wiki/entities/*/*.md")):
        if path.name == "_template.md":
            continue
        rel = path.relative_to(ROOT).as_posix()
        fm = frontmatter(read(path))
        card_type = fm.get("type", "")

        if fm.get("dataset", "") == "demo" or fm.get("synthetic", "") == "true":
            findings.append(Finding("ERROR", rel, "demo/synthetic card found in production `wiki/entities`; keep demo data under `demo/`"))

        entity_id = fm.get("entity_id", "").strip()
        if not entity_id:
            findings.append(Finding("ERROR", rel, "real card missing non-empty `entity_id`"))
        elif entity_id in seen_ids:
            findings.append(Finding("ERROR", rel, f"duplicate `entity_id` also used in {seen_ids[entity_id]}"))
        else:
            seen_ids[entity_id] = rel

        template_version = fm.get("template_version", "").strip()
        if not template_version.isdigit() or int(template_version) < 1:
            findings.append(Finding("ERROR", rel, "`template_version` must be a positive integer"))

        for key in ("created", "updated"):
            if not fm.get(key, "").strip():
                findings.append(Finding("ERROR", rel, f"real card missing non-empty `{key}`"))

        for key in DATE_KEYS:
            value = fm.get(key, "").strip()
            if value and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                findings.append(Finding("ERROR", rel, f"`{key}` must use YYYY-MM-DD"))

        score = fm.get("score", "").strip()
        if score:
            try:
                score_value = float(score)
            except ValueError:
                findings.append(Finding("ERROR", rel, "`score` must be numeric"))
            else:
                if score_value < 0 or score_value > 100:
                    findings.append(Finding("ERROR", rel, "`score` must be between 0 and 100"))

        if card_type in {"company", "person"}:
            normalized = re.sub(r"\s+", " ", path.stem).strip().casefold()
            key = (card_type, normalized)
            if key in seen_names:
                findings.append(Finding("WARN", rel, f"possible duplicate {card_type} name also in {seen_names[key]}"))
            else:
                seen_names[key] = rel


def check_demo_boundary(findings: list[Finding]) -> None:
    """Demo cards must remain explicitly synthetic and isolated under demo/."""
    demo_cards = sorted((ROOT / "demo" / "demo-vault" / "wiki" / "entities").glob("*/*.md"))
    # The permissioned sub-vault keeps cards under demo/permissioned/<boundary>/...
    perm_root = ROOT / "demo" / "permissioned"
    perm_cards = sorted(perm_root.rglob("*.md")) if perm_root.exists() else []
    for path in demo_cards + perm_cards:
        if path.name == "_template.md":
            continue
        rel = path.relative_to(ROOT).as_posix()
        fm = frontmatter(read(path))
        if fm.get("dataset", "") != "demo":
            findings.append(Finding("ERROR", rel, "demo card missing `dataset: demo`"))
        if fm.get("synthetic", "") != "true":
            findings.append(Finding("ERROR", rel, "demo card missing `synthetic: true`"))
        entity_id = fm.get("entity_id", "")
        if not entity_id.startswith("demo-"):
            findings.append(Finding("ERROR", rel, "`entity_id` in demo vault must start with `demo-`"))


def check_pilot_boundary(findings: list[Finding]) -> None:
    """Real pilot data must live outside this repository.

    The pilot contour (`dataset: pilot`) is the controlled real-data vault per
    `wiki/processes/pilot-data-contract.md`; committing it here would mix real
    customer data into a repository that also ships demo data and code.
    """
    pilot_dir = ROOT / "pilot"
    if pilot_dir.exists():
        findings.append(
            Finding(
                "ERROR",
                "pilot",
                "pilot directory found inside the repository; the pilot vault must live "
                "outside this repo per `wiki/processes/pilot-data-contract.md`",
            )
        )
    for path in sorted(ROOT.rglob("*.md")):
        parts = path.relative_to(ROOT).parts
        if parts and (parts[0].startswith(".") or parts[0] in {"__pycache__", "node_modules"}):
            continue
        if frontmatter(read(path)).get("dataset", "") == "pilot":
            findings.append(
                Finding(
                    "ERROR",
                    path.relative_to(ROOT).as_posix(),
                    "`dataset: pilot` card committed inside the repository; pilot data must "
                    "stay outside per `wiki/processes/pilot-data-contract.md`",
                )
            )


def check_scoring_config(findings: list[Finding]) -> None:
    rel = "schemas/scoring-models.json"
    try:
        config = load_json(rel)
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(Finding("ERROR", rel, f"cannot read scoring config: {exc}"))
        return

    allowed_bands = PROPERTY_ALLOWED_VALUES["score_band"]
    allowed_confidence = PROPERTY_ALLOWED_VALUES["score_confidence"]
    allowed_status = CARD_STATUS_ALLOWED["scoring-model"]

    bands = config.get("score_bands", [])
    if not isinstance(bands, list) or not bands:
        findings.append(Finding("ERROR", rel, "`score_bands` must be a non-empty list"))
    else:
        seen_band_ids: set[str] = set()
        ranges: list[tuple[int, int, str]] = []
        for band in bands:
            if not isinstance(band, dict):
                findings.append(Finding("ERROR", rel, "each score band must be an object"))
                continue
            band_id = str(band.get("id", ""))
            seen_band_ids.add(band_id)
            if band_id not in allowed_bands:
                findings.append(Finding("ERROR", rel, f"score band `{band_id}` is not in canonical score_band values"))
            try:
                min_value = int(band.get("min"))
                max_value = int(band.get("max"))
            except (TypeError, ValueError):
                findings.append(Finding("ERROR", rel, f"score band `{band_id}` min/max must be integers"))
                continue
            if min_value < 0 or max_value > 100 or min_value > max_value:
                findings.append(Finding("ERROR", rel, f"score band `{band_id}` range must be within 0-100 and min <= max"))
            ranges.append((min_value, max_value, band_id))
        if seen_band_ids != allowed_bands:
            findings.append(Finding("ERROR", rel, f"score bands {sorted(seen_band_ids)} must match canonical {sorted(allowed_bands)}"))
        expected_min = 0
        for min_value, max_value, band_id in sorted(ranges):
            if min_value != expected_min:
                findings.append(Finding("ERROR", rel, f"score bands have gap/overlap before `{band_id}`; expected min {expected_min}, got {min_value}"))
            expected_min = max_value + 1
        if ranges and expected_min != 101:
            findings.append(Finding("ERROR", rel, "score bands must cover through 100"))

    confidence_rules = config.get("confidence_rules", [])
    if isinstance(confidence_rules, list):
        confidence_ids = {str(rule.get("id", "")) for rule in confidence_rules if isinstance(rule, dict)}
        if confidence_ids != allowed_confidence:
            findings.append(Finding("ERROR", rel, f"confidence rules {sorted(confidence_ids)} must match canonical {sorted(allowed_confidence)}"))
    else:
        findings.append(Finding("ERROR", rel, "`confidence_rules` must be a list"))

    models = config.get("models", {})
    if not isinstance(models, dict) or not models:
        findings.append(Finding("ERROR", rel, "`models` must be a non-empty object"))
        return

    for model_id, model in sorted(models.items()):
        if not isinstance(model, dict):
            findings.append(Finding("ERROR", rel, f"model `{model_id}` must be an object"))
            continue
        status = str(model.get("status", ""))
        if status not in allowed_status:
            findings.append(Finding("ERROR", rel, f"model `{model_id}` status `{status}` is not allowed for scoring-model"))
        if model.get("applies_to") not in {"lead", "deal"}:
            findings.append(Finding("ERROR", rel, f"model `{model_id}` `applies_to` must be `lead` or `deal`"))
        for required in ("version", "owner", "model_ref", "default_next_action"):
            if not str(model.get(required, "")).strip():
                findings.append(Finding("ERROR", rel, f"model `{model_id}` missing `{required}`"))

        dimensions = model.get("dimensions", [])
        if not isinstance(dimensions, list) or not dimensions:
            findings.append(Finding("ERROR", rel, f"model `{model_id}` must have dimensions"))
        else:
            seen_dimensions: set[str] = set()
            total = 0
            for dimension in dimensions:
                if not isinstance(dimension, dict):
                    findings.append(Finding("ERROR", rel, f"model `{model_id}` dimension must be an object"))
                    continue
                dim_id = str(dimension.get("id", ""))
                if not dim_id:
                    findings.append(Finding("ERROR", rel, f"model `{model_id}` dimension missing `id`"))
                elif dim_id in seen_dimensions:
                    findings.append(Finding("ERROR", rel, f"model `{model_id}` duplicate dimension `{dim_id}`"))
                seen_dimensions.add(dim_id)
                try:
                    weight = int(dimension.get("weight"))
                except (TypeError, ValueError):
                    findings.append(Finding("ERROR", rel, f"model `{model_id}` dimension `{dim_id}` weight must be integer"))
                    continue
                if weight < 0 or weight > 100:
                    findings.append(Finding("ERROR", rel, f"model `{model_id}` dimension `{dim_id}` weight must be 0-100"))
                total += weight
            if total != 100:
                findings.append(Finding("ERROR", rel, f"model `{model_id}` weights sum to {total}, expected 100"))

        penalties = model.get("penalties", [])
        if not isinstance(penalties, list):
            findings.append(Finding("ERROR", rel, f"model `{model_id}` penalties must be a list"))
            continue
        for penalty in penalties:
            if not isinstance(penalty, dict):
                findings.append(Finding("ERROR", rel, f"model `{model_id}` penalty must be an object"))
                continue
            penalty_type = penalty.get("type")
            if penalty_type not in {"subtract", "cap", "disqualify"}:
                findings.append(Finding("ERROR", rel, f"model `{model_id}` penalty `{penalty.get('id', '')}` has invalid type `{penalty_type}`"))
            if penalty_type in {"subtract", "cap"}:
                try:
                    value = int(penalty.get("value"))
                except (TypeError, ValueError):
                    findings.append(Finding("ERROR", rel, f"model `{model_id}` penalty `{penalty.get('id', '')}` needs integer value"))
                    continue
                if value < 0 or value > 100:
                    findings.append(Finding("ERROR", rel, f"model `{model_id}` penalty `{penalty.get('id', '')}` value must be 0-100"))


def check_connector_contracts(findings: list[Finding]) -> None:
    rel = "schemas/connector-contracts.json"
    try:
        config = load_json(rel)
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(Finding("ERROR", rel, f"cannot read connector contracts: {exc}"))
        return
    connectors = config.get("connectors", {})
    if not isinstance(connectors, dict) or not connectors:
        findings.append(Finding("ERROR", rel, "`connectors` must be a non-empty object"))
        return
    valid_status = {"planned", "proposed", "manual-first", "active", "disabled"}
    valid_write_modes = {"read-only", "propose-only", "approved-writeback", "system-writeback", "staged-import", "reference-preferred", "curated-write", "approved-send"}
    for connector_id, connector in sorted(connectors.items()):
        if not isinstance(connector, dict):
            findings.append(Finding("ERROR", rel, f"connector `{connector_id}` must be an object"))
            continue
        if connector.get("status") not in valid_status:
            findings.append(Finding("ERROR", rel, f"connector `{connector_id}` has invalid status `{connector.get('status')}`"))
        for key in ("kind", "owner", "audit_log", "failure_mode"):
            if not str(connector.get(key, "")).strip():
                findings.append(Finding("ERROR", rel, f"connector `{connector_id}` missing `{key}`"))
        process_docs = connector.get("process_docs", [])
        if not isinstance(process_docs, list) or not process_docs:
            findings.append(Finding("ERROR", rel, f"connector `{connector_id}` must list process_docs"))
        else:
            for doc in process_docs:
                if not (ROOT / str(doc)).exists():
                    findings.append(Finding("ERROR", rel, f"connector `{connector_id}` references missing process doc `{doc}`"))
        for key in ("read_scopes", "approval_required_for", "forbidden_operations"):
            value = connector.get(key, [])
            if not isinstance(value, list) or not value:
                findings.append(Finding("ERROR", rel, f"connector `{connector_id}` must have non-empty `{key}`"))
        write_modes = connector.get("write_modes", {})
        if not isinstance(write_modes, dict) or not write_modes:
            findings.append(Finding("ERROR", rel, f"connector `{connector_id}` must define write_modes"))
        else:
            for target, mode in write_modes.items():
                if mode not in valid_write_modes:
                    findings.append(Finding("ERROR", rel, f"connector `{connector_id}` write mode for `{target}` is invalid: `{mode}`"))
        collection_methods = connector.get("collection_methods", {})
        if collection_methods and not isinstance(collection_methods, dict):
            findings.append(Finding("ERROR", rel, f"connector `{connector_id}` collection_methods must be an object"))
        elif isinstance(collection_methods, dict):
            for method_id, method in sorted(collection_methods.items()):
                if not isinstance(method, dict):
                    findings.append(Finding("ERROR", rel, f"connector `{connector_id}` collection method `{method_id}` must be an object"))
                    continue
                if not str(method.get("status", "")).strip():
                    findings.append(Finding("ERROR", rel, f"connector `{connector_id}` collection method `{method_id}` missing `status`"))
                allowed_when = method.get("allowed_when", [])
                if not isinstance(allowed_when, list) or not allowed_when:
                    findings.append(Finding("ERROR", rel, f"connector `{connector_id}` collection method `{method_id}` needs non-empty `allowed_when`"))
                artifacts = method.get("artifacts", [])
                if not isinstance(artifacts, list) or not artifacts:
                    findings.append(Finding("ERROR", rel, f"connector `{connector_id}` collection method `{method_id}` needs non-empty `artifacts`"))
                forbidden = method.get("forbidden", [])
                if forbidden and not isinstance(forbidden, list):
                    findings.append(Finding("ERROR", rel, f"connector `{connector_id}` collection method `{method_id}` `forbidden` must be a list"))
                credential_policy = method.get("credential_policy", {})
                if credential_policy and not isinstance(credential_policy, dict):
                    findings.append(Finding("ERROR", rel, f"connector `{connector_id}` collection method `{method_id}` credential_policy must be an object"))
                elif isinstance(credential_policy, dict) and credential_policy:
                    required_keys = ("credential_storage", "repo_storage", "without_backend_key")
                    for key in required_keys:
                        if not str(credential_policy.get(key, "")).strip():
                            findings.append(Finding("ERROR", rel, f"connector `{connector_id}` collection method `{method_id}` credential_policy missing `{key}`"))
                    required_any = credential_policy.get("full_harness_requires_one_of", [])
                    if not isinstance(required_any, list) or not required_any:
                        findings.append(Finding("ERROR", rel, f"connector `{connector_id}` collection method `{method_id}` credential_policy needs full_harness_requires_one_of"))
        writeback_pipeline = connector.get("writeback_pipeline", {})
        if writeback_pipeline and not isinstance(writeback_pipeline, dict):
            findings.append(Finding("ERROR", rel, f"connector `{connector_id}` writeback_pipeline must be an object"))
        elif isinstance(writeback_pipeline, dict) and writeback_pipeline:
            for key in ("default_mode", "proposal_location"):
                if not str(writeback_pipeline.get(key, "")).strip():
                    findings.append(Finding("ERROR", rel, f"connector `{connector_id}` writeback_pipeline missing `{key}`"))
            proposal_location = str(writeback_pipeline.get("proposal_location", ""))
            if proposal_location and not (ROOT / proposal_location).exists():
                findings.append(Finding("ERROR", rel, f"connector `{connector_id}` writeback_pipeline proposal_location missing `{proposal_location}`"))
            for key in ("allowed_card_fill_targets", "requires_before_write", "never_write_without_approval"):
                value = writeback_pipeline.get(key, [])
                if not isinstance(value, list) or not value:
                    findings.append(Finding("ERROR", rel, f"connector `{connector_id}` writeback_pipeline needs non-empty `{key}`"))


def check_event_research_profile(findings: list[Finding]) -> None:
    rel = "schemas/event-research-profile.json"
    try:
        config = load_json(rel)
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(Finding("ERROR", rel, f"cannot read event research profile: {exc}"))
        return
    profiles = config.get("profiles", {})
    default_profile = str(config.get("default_profile", ""))
    if not isinstance(profiles, dict) or not profiles:
        findings.append(Finding("ERROR", rel, "`profiles` must be a non-empty object"))
        return
    if default_profile not in profiles:
        findings.append(Finding("ERROR", rel, f"default_profile `{default_profile}` not found in profiles"))
    required_list_fields = (
        "source_priority",
        "required_outputs",
        "event_fields",
        "participation_fields",
        "company_enrichment_fields",
        "verification",
    )
    for profile_id, profile in sorted(profiles.items()):
        if not isinstance(profile, dict):
            findings.append(Finding("ERROR", rel, f"profile `{profile_id}` must be an object"))
            continue
        for key in ("status", "owner", "mode", "purpose"):
            if not str(profile.get(key, "")).strip():
                findings.append(Finding("ERROR", rel, f"profile `{profile_id}` missing `{key}`"))
        for key in required_list_fields:
            value = profile.get(key, [])
            if not isinstance(value, list) or not value:
                findings.append(Finding("ERROR", rel, f"profile `{profile_id}` must have non-empty `{key}`"))
        action_rules = profile.get("action_rules", {})
        if not isinstance(action_rules, dict) or not action_rules:
            findings.append(Finding("ERROR", rel, f"profile `{profile_id}` must define action_rules"))
        else:
            for key in ("create_outreach_task_only_when", "marketing_content_candidate_when", "block_action_when"):
                value = action_rules.get(key, [])
                if not isinstance(value, list) or not value:
                    findings.append(Finding("ERROR", rel, f"profile `{profile_id}` action_rules missing non-empty `{key}`"))
        pilot_limits = profile.get("pilot_limits", {})
        if not isinstance(pilot_limits, dict) or not pilot_limits:
            findings.append(Finding("ERROR", rel, f"profile `{profile_id}` must define pilot_limits"))
        else:
            for key in ("max_event_sources", "max_companies", "max_people", "max_company_sources"):
                try:
                    value = int(pilot_limits.get(key))
                except (TypeError, ValueError):
                    findings.append(Finding("ERROR", rel, f"profile `{profile_id}` pilot limit `{key}` must be integer"))
                    continue
                if value < 1:
                    findings.append(Finding("ERROR", rel, f"profile `{profile_id}` pilot limit `{key}` must be >= 1"))


def check_permissioned_contracts(findings: list[Finding]) -> None:
    """Validate the permissioned-knowledge Slice 1 contracts and their coherence."""
    try:
        registry = load_json("schemas/boundary-registry.json")
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(Finding("ERROR", "schemas/boundary-registry.json", f"cannot read boundary registry: {exc}"))
        registry = None
    try:
        policy = load_json("schemas/access-policy.json")
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(Finding("ERROR", "schemas/access-policy.json", f"cannot read access policy: {exc}"))
        policy = None
    try:
        idp = load_json("schemas/identity-provider.json")
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(Finding("ERROR", "schemas/identity-provider.json", f"cannot read identity provider: {exc}"))
        idp = None

    boundary_ids: set[str] = set()
    if isinstance(registry, dict):
        rel = "schemas/boundary-registry.json"
        boundaries = registry.get("boundaries", [])
        if not isinstance(boundaries, list) or not boundaries:
            findings.append(Finding("ERROR", rel, "`boundaries` must be a non-empty list"))
        else:
            boundary_ids = {b.get("id", "") for b in boundaries if isinstance(b, dict)}
        if registry.get("default_boundary") not in boundary_ids:
            findings.append(Finding("ERROR", rel, "`default_boundary` must reference a defined boundary"))
        for entry in registry.get("path_map", []):
            if not isinstance(entry, dict) or "prefix" not in entry:
                findings.append(Finding("ERROR", rel, "each path_map entry needs a `prefix`"))
                continue
            if entry.get("boundary") not in boundary_ids:
                findings.append(Finding("ERROR", rel, f"path_map prefix `{entry['prefix']}` maps to unknown boundary"))

    role_ids: set[str] = set()
    if isinstance(policy, dict):
        rel = "schemas/access-policy.json"
        roles = policy.get("roles", [])
        if not isinstance(roles, list) or not roles:
            findings.append(Finding("ERROR", rel, "`roles` must be a non-empty list"))
        else:
            role_ids = {r.get("id", "") for r in roles if isinstance(r, dict)}
            for role in roles:
                if not isinstance(role, dict):
                    continue
                for boundary in role.get("boundaries", []):
                    if boundary_ids and boundary not in boundary_ids:
                        findings.append(Finding("ERROR", rel, f"role `{role.get('id')}` references unknown boundary `{boundary}`"))
        if policy.get("rules", {}).get("personal_data_default") != "deny":
            findings.append(Finding("ERROR", rel, "rules.personal_data_default must be `deny`"))
        for rule_key in ("approver_roles", "reviewer_roles"):
            rule_roles = policy.get("rules", {}).get(rule_key, [])
            if not isinstance(rule_roles, list) or not rule_roles:
                findings.append(Finding("ERROR", rel, f"rules.{rule_key} must be a non-empty list"))
            else:
                for r in rule_roles:
                    if role_ids and r not in role_ids:
                        findings.append(Finding("ERROR", rel, f"rules.{rule_key} references unknown role `{r}`"))

    if isinstance(idp, dict):
        rel = "schemas/identity-provider.json"
        providers = idp.get("providers", {})
        if idp.get("active_provider") not in providers:
            findings.append(Finding("ERROR", rel, "`active_provider` must reference a defined provider"))
        fixture = providers.get("fixture", {}) if isinstance(providers, dict) else {}
        users = fixture.get("users", [])
        if not users:
            findings.append(Finding("ERROR", rel, "fixture provider must define demo users"))
        for user in users:
            if role_ids and user.get("role") not in role_ids:
                findings.append(Finding("ERROR", rel, f"fixture user `{user.get('id')}` has unknown role `{user.get('role')}`"))
        google = providers.get("google-oidc", {}) if isinstance(providers, dict) else {}
        client_id = str(google.get("client_id", ""))
        if client_id.endswith(".apps.googleusercontent.com"):
            findings.append(Finding("ERROR", rel, "identity-provider.json must not contain a real Google client id"))
        for group, role in google.get("group_role_map", {}).items():
            if role_ids and role not in role_ids:
                findings.append(Finding("ERROR", rel, f"google group `{group}` maps to unknown role `{role}`"))

    # Field-extraction profile: the contract between card shapes and the read
    # extractor. Validate structure so it cannot silently drift.
    rel = "schemas/field-extraction.json"
    try:
        field_map = load_json(rel)
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(Finding("ERROR", rel, f"cannot read field-extraction map: {exc}"))
        field_map = {}
    types = field_map.get("types", {}) if isinstance(field_map, dict) else {}
    if not types:
        findings.append(Finding("ERROR", rel, "`types` must be a non-empty map"))
    for card_type, fields in types.items():
        if not isinstance(fields, dict) or not fields:
            findings.append(Finding("ERROR", rel, f"type `{card_type}` must map to a non-empty field set"))
            continue
        for field_name, spec in fields.items():
            if not isinstance(spec, dict) or not spec.get("section"):
                findings.append(Finding("ERROR", rel, f"`{card_type}.{field_name}` must define a non-empty `section`"))
            if "label" in spec and not isinstance(spec["label"], str):
                findings.append(Finding("ERROR", rel, f"`{card_type}.{field_name}` label must be a string"))


# A section heading that marks a raw call/meeting body inside a card. Boundaries
# declared `raw_bodies_allowed: false` in the registry may hold handles/metadata
# and sanitized extracts only — never this section.
RAW_TRANSCRIPT_MARKER = re.compile(r"(?im)^#{1,6}\s.*raw transcript")


def check_permissioned_data_integrity(findings: list[Finding], perm_root: Path | None = None,
                                      registry: dict | None = None) -> None:
    """Referential + ownership + boundary integrity for the permissioned vault.

    Closes risks #2/#5/#11: card boundary must match its folder (single source of
    truth), `company:` references must resolve, and sales-confidential ownership
    attributes (owner/team) must be in the org roster so a typo cannot silently
    mis-route access. Also enforces the registry's `raw_bodies_allowed: false`
    contract (e.g. personal-data holds handles + sanitized extracts, never a raw
    transcript body). `perm_root` and `registry` are overridable for tests.
    """
    perm_root = Path(perm_root) if perm_root else ROOT / "demo" / "permissioned"
    if not perm_root.exists():
        return
    if registry is None:
        try:
            registry = load_json("schemas/boundary-registry.json")
        except (OSError, json.JSONDecodeError):
            return
    path_map = registry.get("path_map", [])
    # Fail-closed default: a path outside every prefix must not be world-readable.
    default_boundary = registry.get("default_boundary") or "quarantine"
    no_raw_bodies = {b.get("id") for b in registry.get("boundaries", [])
                     if b.get("raw_bodies_allowed") is False}

    def resolve_boundary(rel_path: str) -> str | None:
        """The boundary a path prefix maps to, or None when NO prefix matches.
        None is distinct from the default boundary on purpose: a prefix may
        legitimately map to the default boundary (e.g. a legacy registry with
        default_boundary 'broad'), and that is not a misfiled card."""
        for entry in path_map:
            if rel_path.startswith(entry.get("prefix", "\0")):
                return entry.get("boundary", default_boundary)
        return None

    org = load_json("schemas/identity-provider.json").get("org", {})
    actors = set(org.get("actors", []))
    teams = set(org.get("teams", []))

    cards = sorted(perm_root.rglob("*.md"))
    company_ids = set()
    for path in cards:
        fm = frontmatter(read(path))
        if fm.get("type") == "company" and fm.get("entity_id"):
            company_ids.add(fm["entity_id"])

    for path in cards:
        rel_root = path.relative_to(perm_root).as_posix()
        rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else rel_root
        text = read(path)
        fm = frontmatter(text)
        resolved = resolve_boundary(rel_root)
        if resolved is None:
            findings.append(Finding("ERROR", rel, f"card is outside every known boundary prefix; it would fail closed (`{default_boundary}`) — file it under a boundary folder"))
            continue
        if resolved in no_raw_bodies and RAW_TRANSCRIPT_MARKER.search(text):
            findings.append(Finding("ERROR", rel, f"boundary `{resolved}` declares `raw_bodies_allowed: false` but the card embeds a raw-transcript section — store an opaque handle plus a sanitized extract instead"))
        declared = fm.get("boundary", "")
        if declared and declared != resolved:
            findings.append(Finding("ERROR", rel, f"`boundary: {declared}` disagrees with its folder boundary `{resolved}`"))
        company_ref = fm.get("company", "")
        if company_ref and company_ids and company_ref not in company_ids:
            findings.append(Finding("ERROR", rel, f"`company: {company_ref}` does not resolve to a known company card"))
        if resolved == "sales-confidential":
            owner = fm.get("owner", "")
            team = fm.get("team", "")
            if actors and owner and owner not in actors:
                findings.append(Finding("ERROR", rel, f"sales-confidential `owner: {owner}` is not in the org roster"))
            if teams and team and team not in teams:
                findings.append(Finding("ERROR", rel, f"sales-confidential `team: {team}` is not in the org roster"))


def check_id_ledger(findings: list[Finding], path: Path | None = None) -> None:
    """Validate the entity-id ledger if it exists (no-op otherwise).

    Enforces the identifier strategy: ids are typed opaque ULIDs, globally unique,
    and natural keys are idempotent per type. See identifier-strategy.md.
    `path` is overridable for tests.
    """
    path = Path(path) if path else ROOT / "state" / "id-ledger.jsonl"
    if not path.exists():
        return
    rel = path.name if path.is_absolute() and not path.is_relative_to(ROOT) else "state/id-ledger.jsonl"
    import re as _re
    id_pattern = _re.compile(r"^[a-z0-9-]+_[0-9A-HJKMNP-TV-Z]{26}$")
    seen_ids: dict[str, int] = {}
    seen_keys: dict[tuple[str, str], str] = {}
    for n, line in enumerate(read(path).splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            findings.append(Finding("ERROR", rel, f"line {n} is not valid JSON"))
            continue
        cid, ctype = rec.get("id", ""), rec.get("type", "")
        if not cid or not ctype:
            findings.append(Finding("ERROR", rel, f"line {n} missing `id` or `type`"))
            continue
        if not id_pattern.match(cid) or not cid.startswith(f"{ctype}_"):
            findings.append(Finding("ERROR", rel, f"id `{cid}` does not match the typed-ULID scheme for type `{ctype}`"))
        if cid in seen_ids:
            findings.append(Finding("ERROR", rel, f"duplicate id `{cid}` (also line {seen_ids[cid]})"))
        seen_ids[cid] = n
        nkey = rec.get("natural_key", "")
        if nkey:
            key = (ctype, nkey)
            if key in seen_keys and seen_keys[key] != cid:
                findings.append(Finding("ERROR", rel, f"natural key `{ctype}/{nkey}` maps to two ids ({seen_keys[key]}, {cid})"))
            seen_keys[key] = cid


def check_agent_routing(findings: list[Finding]) -> None:
    rel = "schemas/agent-routing.json"
    try:
        config = load_json(rel)
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(Finding("ERROR", rel, f"cannot read agent routing: {exc}"))
        return
    agents = config.get("agents", {})
    skills = config.get("skills", {})
    routes = config.get("routes", [])
    if not isinstance(agents, dict) or not agents:
        findings.append(Finding("ERROR", rel, "`agents` must be a non-empty object"))
        return
    if not isinstance(skills, dict) or not skills:
        findings.append(Finding("ERROR", rel, "`skills` must be a non-empty object"))
        return
    valid_status = {"active", "proposed", "disabled"}
    for skill_id, skill in sorted(skills.items()):
        if not isinstance(skill, dict):
            findings.append(Finding("ERROR", rel, f"skill `{skill_id}` must be an object"))
            continue
        path = str(skill.get("path", ""))
        if not path or not (ROOT / path).exists():
            findings.append(Finding("ERROR", rel, f"skill `{skill_id}` references missing path `{path}`"))
    for agent_id, agent in sorted(agents.items()):
        if not isinstance(agent, dict):
            findings.append(Finding("ERROR", rel, f"agent `{agent_id}` must be an object"))
            continue
        if agent.get("status") not in valid_status:
            findings.append(Finding("ERROR", rel, f"agent `{agent_id}` has invalid status `{agent.get('status')}`"))
        path = str(agent.get("path", ""))
        if not path or not (ROOT / path).exists():
            findings.append(Finding("ERROR", rel, f"agent `{agent_id}` references missing path `{path}`"))
        for key in ("mode", "writes"):
            if not str(agent.get(key, "")).strip():
                findings.append(Finding("ERROR", rel, f"agent `{agent_id}` missing `{key}`"))
    if not isinstance(routes, list) or not routes:
        findings.append(Finding("ERROR", rel, "`routes` must be a non-empty list"))
        return
    for route in routes:
        if not isinstance(route, dict):
            findings.append(Finding("ERROR", rel, "each route must be an object"))
            continue
        intent = route.get("intent", "")
        primary_agent = route.get("primary_agent")
        primary_skill = route.get("primary_skill")
        if not intent:
            findings.append(Finding("ERROR", rel, "route missing `intent`"))
        if not primary_agent and not primary_skill:
            findings.append(Finding("ERROR", rel, f"route `{intent}` needs primary_agent or primary_skill"))
        if primary_agent and primary_agent not in agents:
            findings.append(Finding("ERROR", rel, f"route `{intent}` references unknown primary_agent `{primary_agent}`"))
        if primary_skill and primary_skill not in skills:
            findings.append(Finding("ERROR", rel, f"route `{intent}` references unknown primary_skill `{primary_skill}`"))
        for key, known in (("skills", skills), ("handoffs", agents), ("verification", agents)):
            values = route.get(key, [])
            if values and not isinstance(values, list):
                findings.append(Finding("ERROR", rel, f"route `{intent}` `{key}` must be a list"))
                continue
            for value in values:
                if value not in known:
                    findings.append(Finding("ERROR", rel, f"route `{intent}` references unknown {key[:-1]} `{value}`"))


def check_agent_tool_guardrails(findings: list[Finding]) -> None:
    for path in sorted(ROOT.glob(".claude/agents/*.md")):
        if path.name == "README.md":
            continue
        rel = path.relative_to(ROOT).as_posix()
        fm = frontmatter(read(path))
        tools = fm.get("tools", "")
        if any(tool in tools for tool in ("Edit", "Write", "Bash")):
            text = read(path).lower()
            if "guardrails" not in text:
                findings.append(Finding("ERROR", rel, "agent with write/bash tools must have Guardrails section"))
            if "approval" not in text and "approved" not in text and "health_check" not in text and "health check" not in text:
                findings.append(Finding("WARN", rel, "agent with write/bash tools should mention approval or verification guardrail"))


def check_lead_template_vocabularies(findings: list[Finding]) -> None:
    """Keep human-facing lead template hints aligned with the canonical enums."""
    path = ROOT / "wiki/entities/leads/_template.md"
    if not path.exists():
        return
    rel = path.relative_to(ROOT).as_posix()
    text = read(path)
    expected = {
        "Lead type:": PROPERTY_ALLOWED_VALUES["lead_type"],
        "Pipeline segment:": PROPERTY_ALLOWED_VALUES["pipeline_segment"],
    }
    for prefix, allowed in expected.items():
        match = re.search(rf"^{re.escape(prefix)}\s+`([^`]+)`", text, flags=re.MULTILINE)
        if not match:
            findings.append(Finding("ERROR", rel, f"missing `{prefix}` vocabulary hint"))
            continue
        values = {part.strip() for part in match.group(1).split("|")}
        if values != allowed:
            findings.append(
                Finding("ERROR", rel, f"`{prefix}` values {sorted(values)} do not match canonical {sorted(allowed)}")
            )


def check_hubspot_pipeline_mapping(findings: list[Finding]) -> None:
    """Validate the pipeline_segment column in the HubSpot lifecycle mapping table."""
    path = ROOT / "wiki/processes/hubspot-lifecycle-mapping.md"
    if not path.exists():
        return
    rel = path.relative_to(ROOT).as_posix()
    text = read(path)
    marker = "## Lead Pipeline Segment Mapping"
    start = text.find(marker)
    if start == -1:
        findings.append(Finding("ERROR", rel, "missing `Lead Pipeline Segment Mapping` section"))
        return
    end = text.find("\n## ", start + len(marker))
    section = text[start : end if end != -1 else len(text)]
    for line in section.splitlines():
        if not line.startswith("|") or "`" not in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2 or cells[1] == "SalesWiki `pipeline_segment`":
            continue
        match = re.fullmatch(r"`([^`]+)`", cells[1])
        if not match:
            continue
        value = match.group(1)
        if value not in PROPERTY_ALLOWED_VALUES["pipeline_segment"]:
            findings.append(
                Finding("ERROR", rel, f"pipeline mapping uses `{value}`; expected one of {sorted(PROPERTY_ALLOWED_VALUES['pipeline_segment'])}")
            )


def check_workflow_contracts(findings: list[Finding]) -> None:
    """Check high-risk sales workflow contracts that structure-only linting misses."""
    lead_template = ROOT / "wiki/entities/leads/_template.md"
    if lead_template.exists():
        rel = lead_template.relative_to(ROOT).as_posix()
        text = read(lead_template)
        for snippet in ("- Action:", "- Due:", "- Owner:", "- Related task:", "- No-action reason:"):
            if snippet not in text:
                findings.append(Finding("ERROR", rel, f"lead next-action contract missing `{snippet}`"))

    call_template = ROOT / "wiki/entities/calls/_template.md"
    if call_template.exists():
        rel = call_template.relative_to(ROOT).as_posix()
        text = read(call_template)
        for snippet in ("- Lead page:", "- Deal page:"):
            if snippet not in text:
                findings.append(Finding("ERROR", rel, f"call propagation contract missing `{snippet}`"))

    lead_agent = ROOT / ".claude/agents/lead-monitor.md"
    if lead_agent.exists():
        rel = lead_agent.relative_to(ROOT).as_posix()
        text = read(lead_agent)
        for snippet in ("create a `Task`", "owner", "due date", "no-action reason"):
            if snippet not in text:
                findings.append(Finding("ERROR", rel, f"lead-monitor contract missing `{snippet}`"))

    call_agent = ROOT / ".claude/agents/call-analyst.md"
    if call_agent.exists():
        rel = call_agent.relative_to(ROOT).as_posix()
        text = read(call_agent)
        for snippet in ("Update linked Deal/Lead", "re-score"):
            if snippet not in text:
                findings.append(Finding("ERROR", rel, f"call-analyst contract missing `{snippet}`"))


def check_links_to_core_docs(findings: list[Finding]) -> None:
    index_path = ROOT / "wiki/index.md"
    if not index_path.exists():
        return
    index_text = read(index_path)
    for rel in REQUIRED_FILES:
        if rel.startswith("wiki/processes/") and rel not in index_text:
            findings.append(Finding("WARN", "wiki/index.md", f"does not reference `{rel}`"))


def template_property_union() -> set[str]:
    """All frontmatter keys declared by at least one entity template."""
    keys: set[str] = set()
    for path in sorted(ROOT.glob(ENTITY_TEMPLATE_GLOB)):
        keys.update(frontmatter(read(path)).keys())
    return keys


# Tokens that look like properties in `.base` files but are built-ins or functions.
_BASE_BUILTIN_PREFIXES = ("file.", "formula.")
_BASE_FUNCS = {"date", "today", "now", "if", "link", "number", "duration", "min", "max", "and", "or"}


def base_referenced_properties(text: str) -> set[str]:
    """Extract property identifiers referenced by an Obsidian Bases `.base` file."""
    props: set[str] = set()

    # 1. keys under the top-level `properties:` block (indented two spaces)
    in_props = False
    for line in text.splitlines():
        if re.match(r"^properties:\s*$", line):
            in_props = True
            continue
        if in_props:
            if re.match(r"^\S", line):  # dedent back to column 0 -> block ended
                in_props = False
            else:
                m = re.match(r"^  ([A-Za-z_][\w.]*):", line)
                if m:
                    props.add(m.group(1))

    # 2. `order:` list entries like `      - freshness`
    for m in re.finditer(r"^\s*-\s+([A-Za-z_][\w.]*)\s*$", text, flags=re.MULTILINE):
        props.add(m.group(1))

    # 3. left-hand side of comparisons inside quoted filter strings
    for m in re.finditer(r"([A-Za-z_][\w.]*)\s*(?:==|!=|<=|>=|<|>)", text):
        props.add(m.group(1))

    cleaned = set()
    for p in props:
        if p.startswith(_BASE_BUILTIN_PREFIXES):
            continue
        if p in _BASE_FUNCS:
            continue
        cleaned.add(p)
    return cleaned


def check_dashboard_property_coherence(findings: list[Finding]) -> None:
    """Every property a dashboard references must exist in at least one template."""
    union = template_property_union()
    if not union:
        return
    for rel in REQUIRED_DASHBOARDS:
        path = ROOT / rel
        if not path.exists():
            continue
        for prop in sorted(base_referenced_properties(read(path))):
            if prop not in union:
                findings.append(
                    Finding("ERROR", rel, f"references property `{prop}` not declared in any entity template")
                )


def check_freshness_coverage(findings: list[Finding]) -> None:
    """`freshness` is a global property; every entity template should declare it."""
    for path in sorted(ROOT.glob(ENTITY_TEMPLATE_GLOB)):
        fm = frontmatter(read(path))
        if fm and "freshness" not in fm:
            rel = path.relative_to(ROOT).as_posix()
            findings.append(Finding("WARN", rel, "template does not declare `freshness` property"))


def check_duplicate_doc_links(findings: list[Finding]) -> None:
    """Catch the same process doc linked twice in README / index."""
    for rel in ("README.md", "wiki/index.md"):
        path = ROOT / rel
        if not path.exists():
            continue
        targets = re.findall(r"wiki/processes/[\w./-]+\.md", read(path))
        counts: dict[str, int] = {}
        for t in targets:
            counts[t] = counts.get(t, 0) + 1
        for target, count in sorted(counts.items()):
            if count > 1:
                findings.append(Finding("WARN", rel, f"links `{target}` {count} times (duplicate)"))


# Agent Skills spec (https://agentskills.io/specification)
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SKILL_ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}


def check_skill_spec(findings: list[Finding]) -> None:
    """Validate every SKILL.md against the open Agent Skills format."""
    skills = sorted(ROOT.glob(".claude/skills/*/SKILL.md"))
    for path in skills:
        rel = path.relative_to(ROOT).as_posix()
        text = read(path)
        if not text.startswith("---\n"):
            findings.append(Finding("ERROR", rel, "SKILL.md missing YAML frontmatter"))
            continue
        fm = frontmatter(text)

        # name
        name = fm.get("name", "")
        dir_name = path.parent.name
        if not name:
            findings.append(Finding("ERROR", rel, "missing required `name`"))
        else:
            if not SKILL_NAME_RE.match(name) or len(name) > 64:
                findings.append(
                    Finding("ERROR", rel, f"`name` `{name}` violates spec (1-64 chars, lowercase a-z/0-9/-, no leading/trailing/double hyphen)")
                )
            if name != dir_name:
                findings.append(Finding("ERROR", rel, f"`name` `{name}` must match parent directory `{dir_name}`"))

        # description
        desc = fm.get("description", "")
        if not desc:
            findings.append(Finding("ERROR", rel, "missing or empty required `description`"))
        elif len(desc) > 1024:
            findings.append(Finding("ERROR", rel, f"`description` is {len(desc)} chars (max 1024)"))

        # compatibility (optional)
        compat = fm.get("compatibility")
        if compat is not None and len(compat) > 500:
            findings.append(Finding("ERROR", rel, f"`compatibility` is {len(compat)} chars (max 500)"))

        # only spec-defined top-level keys
        for key in fm:
            if key not in SKILL_ALLOWED_KEYS:
                findings.append(Finding("WARN", rel, f"frontmatter key `{key}` is not in the Agent Skills spec (use `metadata:` for custom fields)"))

        # body length (progressive disclosure guidance)
        end = text.find("\n---", 4)
        body_lines = text[end + 4 :].count("\n") if end != -1 else 0
        if body_lines > 500:
            findings.append(Finding("WARN", rel, f"SKILL.md body is {body_lines} lines (>500); move detail into references/"))


def check_dangling_wikilinks(findings: list[Finding]) -> None:
    """Flag [[wikilinks]] in real entity cards that do not resolve to a vault page.

    Scoped to instantiated cards (not `_template.md` and not process docs), which
    contain illustrative placeholders rather than real links.
    """
    stems = {p.stem for p in ROOT.glob("wiki/**/*.md")}
    for path in sorted(ROOT.glob("wiki/entities/*/*.md")):
        if path.name == "_template.md":
            continue
        rel = path.relative_to(ROOT).as_posix()
        for m in re.finditer(r"\[\[([^\]]+)\]\]", read(path)):
            target = m.group(1).split("|", 1)[0].split("#", 1)[0].strip()
            if not target or any(ch in target for ch in "<>…"):
                continue
            if target not in stems:
                findings.append(Finding("WARN", rel, f"wikilink `[[{target}]]` does not resolve"))


def main() -> int:
    findings: list[Finding] = []
    check_required_files(findings)
    check_raw_dirs(findings)
    check_dashboards(findings)
    check_entity_templates(findings)
    check_frontmatter_allowed_values(findings)
    check_real_card_data_quality(findings)
    check_demo_boundary(findings)
    check_pilot_boundary(findings)
    check_scoring_config(findings)
    check_connector_contracts(findings)
    check_event_research_profile(findings)
    check_agent_routing(findings)
    check_permissioned_contracts(findings)
    check_permissioned_data_integrity(findings)
    check_id_ledger(findings)
    check_agent_tool_guardrails(findings)
    check_lead_template_vocabularies(findings)
    check_hubspot_pipeline_mapping(findings)
    check_workflow_contracts(findings)
    check_links_to_core_docs(findings)
    check_dashboard_property_coherence(findings)
    check_freshness_coverage(findings)
    check_duplicate_doc_links(findings)
    check_skill_spec(findings)
    check_dangling_wikilinks(findings)

    errors = [f for f in findings if f.severity == "ERROR"]
    warnings = [f for f in findings if f.severity == "WARN"]

    print("SalesWiki health check")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    if findings:
        print()
        for finding in findings:
            print(finding.render())

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

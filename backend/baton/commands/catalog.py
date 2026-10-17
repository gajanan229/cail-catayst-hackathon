"""Command catalog (MVP spec §8.1, §16.1): YAML entries validated at load time."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ParamSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["int", "cpu", "process", "server_class", "volume", "enum"]
    source: str | None = None
    min: int | None = None
    max: int | None = None
    max_from: str | None = None
    state: str | None = None
    choices: list[str] | None = None
    default: Any = None
    required: bool = True


class Example(BaseModel):
    utterance: str
    params: dict[str, Any] = {}


class CatalogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    utility: str
    interpreter: str | None
    template: str | None
    description: str
    tier: Literal["T0", "T1", "T2", "T3"]
    tier_modifiers: list[dict] = []
    tier_rules: str | None = None
    params: dict[str, ParamSpec] = {}
    reversible: bool = False
    undo: dict | None = None
    undo_template: str | None = None
    preconditions: list[str] = []
    side_effects: str
    risks: str
    verification: dict | None = None
    parser: str
    param_class: str = "any"
    facts: str = ""
    doc_refs: list[dict] = []
    examples: list[Example] = []
    aliases: list[str] = []
    syntax_status: Literal["simulated", "verified"] = "simulated"
    internal: bool = False
    blocked: bool = False
    escalation: str | None = None

    @property
    def is_mutating(self) -> bool:
        return self.tier in ("T1", "T2", "T3")


class Catalog:
    def __init__(self, directory: Path):
        self.entries: dict[str, CatalogEntry] = {}
        for path in sorted(directory.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            entry = CatalogEntry.model_validate(data)
            if entry.id != path.stem:
                raise ValueError(f"{path.name}: id {entry.id} does not match the file name")
            self.entries[entry.id] = entry
        self.fixtures_dir = directory / "fixtures"

    def get(self, catalog_id: str) -> CatalogEntry | None:
        return self.entries.get(catalog_id)

    def __contains__(self, catalog_id: str) -> bool:
        return catalog_id in self.entries

    def all(self) -> list[CatalogEntry]:
        return list(self.entries.values())

    def public_entries(self) -> list[dict]:
        out = []
        for e in self.entries.values():
            params = []
            for name, p in e.params.items():
                params.append({"name": name, "type": p.type, "required": p.required, "min": p.min, "max": p.max,
                               "max_from": p.max_from, "source": p.source, "choices": p.choices, "description": None})
            out.append({
                "id": e.id, "title": e.title, "description": e.description, "interpreter": e.interpreter,
                "template": e.template, "syntax_status": e.syntax_status, "tier": e.tier,
                "tier_rules": e.tier_rules or e.tier, "params": params, "reversible": e.reversible,
                "undo_template": e.undo_template, "side_effects": e.side_effects, "risks": e.risks,
                "internal": e.internal, "blocked": e.blocked, "escalation": e.escalation, "aliases": e.aliases,
                "utility": e.utility,
            })
        return out

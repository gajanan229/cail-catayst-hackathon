"""Validator and renderer (MVP spec §8.2): schema, inventory values, preconditions, protected list,
NUMSTATIC ≤ MAXSERVERS (PATHWAY 2049), effective tier, parameter class, rendered text, undo."""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Any

from .catalog import CatalogEntry

SAFE_VALUE = re.compile(r"^[A-Za-z0-9$\-_]{1,24}$")
PROCESS_RE = re.compile(r"^\$[A-Z][A-Z0-9]{0,6}$")
CLASS_ALIASES = {
    "ATM AUTH": "ATM-AUTH", "ATMAUTH": "ATM-AUTH", "ATM": "ATM-AUTH", "ATM AUTHORIZATION": "ATM-AUTH",
    "POS AUTH": "POS-AUTH", "POSAUTH": "POS-AUTH", "POS": "POS-AUTH", "POS AUTHORIZATION": "POS-AUTH",
    "BAL INQ": "BAL-INQ", "BALANCE INQUIRY": "BAL-INQ", "BALINQ": "BAL-INQ", "BALANCE": "BAL-INQ",
    "CARD MGMT": "CARD-MGMT", "CARD MANAGEMENT": "CARD-MGMT", "CARD MAINTENANCE": "CARD-MGMT", "CARDMGMT": "CARD-MGMT",
}


@dataclass
class Inventory:
    """What the validator needs to know about the (simulated) system right now."""
    cpus_up: dict[int, bool]
    processes: dict[str, dict]          # name -> {state, tags, protected, priority, cpu}
    classes: dict[str, dict]            # name -> {tag, numstatic, maxservers}
    volumes: list[str]
    protected_patterns: list[str] = field(default_factory=list)

    def is_protected(self, name: str) -> bool:
        return any(fnmatch.fnmatchcase(name, p) for p in self.protected_patterns) or \
            bool(self.processes.get(name, {}).get("protected"))


@dataclass
class Validation:
    valid: bool
    errors: list[str]
    params: dict[str, Any]
    rendered: str | None
    tier: str
    param_class: str
    undo: dict | None = None
    undo_rendered: str | None = None
    target: str | None = None
    previous: dict = field(default_factory=dict)


def normalize_class(value: Any) -> str:
    text = str(value).strip().upper().replace("_", "-")
    return CLASS_ALIASES.get(text.replace("-", " "), CLASS_ALIASES.get(text, text))


def command_line(entry: CatalogEntry, body: str) -> str:
    """Ghost-typed form: 'INTERPRETER; COMMAND' for subsystem utilities, bare for TACL."""
    if entry.interpreter:
        return f"{entry.interpreter}; {body}"
    return body


def render_template(template: str, params: dict[str, Any]) -> str:
    values = {}
    for k, v in params.items():
        s = str(v)
        if not SAFE_VALUE.match(s):
            raise ValueError(f"unsafe value for {k}: {s!r}")
        values[k] = s
    return template.format(**values)


def validate(entry: CatalogEntry, raw_params: dict[str, Any], inv: Inventory) -> Validation:
    errors: list[str] = []
    params: dict[str, Any] = {}
    previous: dict[str, Any] = {}
    for name, spec in entry.params.items():
        if name not in raw_params or raw_params[name] in (None, ""):
            if spec.default is not None:
                params[name] = spec.default
                continue
            if spec.required:
                errors.append(f"Missing parameter '{name}'")
            continue
        value = raw_params[name]
        try:
            if spec.type in ("int", "cpu"):
                value = int(str(value).strip())
                lo = spec.min if spec.min is not None else (0 if spec.type == "cpu" else None)
                hi = spec.max if spec.max is not None else (len(inv.cpus_up) - 1 if spec.type == "cpu" else None)
                if lo is not None and value < lo:
                    errors.append(f"{name} must be at least {lo}")
                if hi is not None and value > hi:
                    errors.append(f"{name} must be at most {hi}")
                if spec.type == "cpu" and spec.state == "up" and not inv.cpus_up.get(value, False):
                    errors.append(f"CPU {value} is not up")
            elif spec.type == "process":
                value = str(value).strip().upper()
                if not value.startswith("$"):
                    value = "$" + value
                if not PROCESS_RE.match(value):
                    errors.append(f"'{value}' is not a valid process name")
                elif value not in inv.processes:
                    errors.append(f"Process {value} does not exist on \\TORBANK")
                elif spec.state and inv.processes[value].get("state") != spec.state:
                    errors.append(f"Process {value} is {inv.processes[value].get('state', 'unknown').lower()}, not {spec.state.lower()}")
            elif spec.type == "server_class":
                value = normalize_class(value)
                if value not in inv.classes:
                    errors.append(f"Server class {value} does not exist in PATHMON $PM1")
            elif spec.type == "volume":
                value = str(value).strip().upper()
                if not value.startswith("$"):
                    value = "$" + value
                if value not in inv.volumes:
                    errors.append(f"Volume {value} does not exist")
            elif spec.type == "enum":
                choices = spec.choices or []
                match = next((c for c in choices if c.lower() == str(value).strip().lower()), None)
                if match is None:
                    errors.append(f"{name} must be one of {', '.join(choices)}")
                value = match or value
        except (TypeError, ValueError):
            errors.append(f"{name}: invalid value {value!r}")
        params[name] = value
    for extra in set(raw_params) - set(entry.params):
        errors.append(f"Unknown parameter '{extra}'")

    # domain rules
    cls = inv.classes.get(params.get("server_class", ""), {})
    if entry.id == "pathcom.alter_numstatic" and cls and isinstance(params.get("n"), int):
        previous["n"] = cls.get("numstatic")
        if params["n"] > cls.get("maxservers", 0):
            errors.append(f"NUMSTATIC {params['n']} exceeds MAXSERVERS {cls['maxservers']} "
                          f"(PATHWAY 2049, NUMSTATIC EXCEEDS MAXSERVERS)")
    if entry.id == "pathcom.alter_maxservers" and cls and isinstance(params.get("n"), int):
        previous["n"] = cls.get("maxservers")
        if params["n"] < cls.get("numstatic", 0):
            errors.append(f"MAXSERVERS {params['n']} is below NUMSTATIC {cls['numstatic']} (PATHWAY 2049)")
    if entry.id == "tacl.altpri_process" and params.get("process") in inv.processes:
        previous["priority"] = inv.processes[params["process"]].get("priority")

    tier = effective_tier(entry, params, inv)
    param_class = param_class_for(entry, params, inv)
    target = params.get("process") or params.get("server_class") or params.get("volume") or \
        (f"CPU {params['cpu']}" if "cpu" in params else None)

    rendered = None
    undo = None
    undo_rendered = None
    if entry.template:
        try:
            rendered = command_line(entry, render_template(entry.template, params)) if not errors else \
                command_line(entry, entry.template.format(**{k: params.get(k, "{" + k + "}") for k in entry.params}))
        except (ValueError, KeyError) as e:
            errors.append(str(e))
    if entry.undo and not errors:
        up = {}
        for k, v in entry.undo["params"].items():
            if isinstance(v, str) and v.startswith("{previous."):
                up[k] = previous.get(v[len("{previous."):-1])
            elif isinstance(v, str) and v.startswith("{") and v.endswith("}"):
                up[k] = params.get(v[1:-1])
            else:
                up[k] = v
        undo = {"catalog_id": entry.undo["catalog_id"], "params": up}
        if entry.undo_template:
            try:
                fmt = {**params, **{f"previous.{k}": v for k, v in previous.items()}}
                body = entry.undo_template.replace("{previous.", "{previous_")
                fmt2 = {k.replace("previous.", "previous_"): v for k, v in fmt.items()}
                undo_rendered = command_line(entry, render_template(body, fmt2))
            except (ValueError, KeyError):
                undo_rendered = None
    return Validation(valid=not errors, errors=errors, params=params, rendered=rendered, tier=tier,
                      param_class=param_class, undo=undo, undo_rendered=undo_rendered, target=target, previous=previous)


def effective_tier(entry: CatalogEntry, params: dict, inv: Inventory) -> str:
    for mod in entry.tier_modifiers:
        cond = mod.get("when", {})
        ok = True
        for key, want in cond.items():
            obj, _, attr = key.partition(".")
            if obj == "process":
                tags = inv.processes.get(params.get("process", ""), {}).get("tags", [])
                ok = ok and attr == "tag" and want in tags
            elif obj == "server_class":
                ok = ok and inv.classes.get(params.get("server_class", ""), {}).get("tag") == want
            else:
                ok = False
        if ok:
            return mod["tier"]
    return entry.tier


def param_class_for(entry: CatalogEntry, params: dict, inv: Inventory) -> str:
    if entry.param_class == "process_tag":
        tags = inv.processes.get(params.get("process", ""), {}).get("tags", [])
        return "batch" if "batch" in tags else "system" if "system" in tags else "any"
    if entry.param_class == "class_tag":
        return inv.classes.get(params.get("server_class", ""), {}).get("tag", "any")
    return "any"

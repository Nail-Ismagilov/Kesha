"""Glue between the app (GUI / plans / reports) and the standalone dogwatch package.

All logic that is not Tk lives here so it can be tested without a display.
Nothing in this module changes a dog folder: dogwatch only reads them, and the
only things written are dogwatch's own state file and the GEÄNDERT section of a
category report.
"""
import os
from dataclasses import dataclass, field

from dogwatch import DogRef, Store, run

CHANGED_SECTION = "GEÄNDERT:"
DB_NAME = "dogwatch.db"
DEFAULT_WORKERS = 6


@dataclass
class Summary:
    changed: dict = field(default_factory=dict)   # gender -> {dog name: [reasons]}
    n_changed: int = 0
    checked: int = 0
    baselined: int = 0
    cached: int = 0
    warnings: list = field(default_factory=list)  # "key: message"
    errors: list = field(default_factory=list)    # "key: message"
    seconds: float = 0.0


def build_dog_refs(plans, dogs_path, reist_bald):
    """[(gender, DogRef)] for every online dog of every healthy plan.

    "reist bald" dogs are skipped (they never get a folder). A dog without a
    local folder is still checked (description / price), just not its photos.
    """
    pairs = []
    for p in plans:
        if p.error or p.doglist is None:
            continue
        for pet in p.doglist.pets:
            if pet["spec"] in reist_bald:
                continue
            name = pet["name"]
            folder = os.path.join(dogs_path, p.gender, name)
            pairs.append((p.gender, DogRef(
                key=f"{p.gender}/{name}", name=name, url=pet["url"],
                folder=folder if os.path.isdir(folder) else "")))
    return pairs


def reason_for(finding):
    """Human-readable German reason for one dogwatch Finding."""
    d = finding.detail
    return {
        "price": f"Schutzgebühr {d}",
        "description": f"Beschreibung geändert ({d})",
        "photo_count": f"Fotozahl {d}",
    }.get(finding.kind, d or finding.kind)       # first_photo: detail is already a sentence


def write_changed_section(report_path, gender, entries):
    """Write/replace the GEÄNDERT section at the end of <gender>_report.txt.

    entries: {dog name: [reasons]}. The "    * name" lines match the other report
    sections, so the existing report parser and the clickable views keep working;
    the line below holds the reasons. Written atomically (temp file + replace).
    """
    path = os.path.join(report_path, f"{gender}_report.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        text = ""
    idx = text.find("\n" + CHANGED_SECTION)
    if idx != -1:
        text = text[:idx]
    text = (text.rstrip("\n") + "\n") if text else ""
    text += "\n" + CHANGED_SECTION + "\n"
    for name, reasons in entries.items():
        text += f"    * {name}\n        \u2192 {'; '.join(reasons)}\n"
    os.makedirs(report_path, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def parse_changed_entries(report_text):
    """Entries of the GEÄNDERT section as [(dog_name, reasons_text), ...]."""
    lines = report_text.splitlines()
    in_section = False
    entries = []
    for i, line in enumerate(lines):
        s = line.strip()
        if s.upper() == CHANGED_SECTION:
            in_section = True
            continue
        if not in_section:
            continue
        if s == "" or s.endswith(":"):
            break
        if s.startswith("*"):
            reason = ""
            if i + 1 < len(lines) and lines[i + 1].strip().startswith("\u2192"):
                reason = lines[i + 1].strip().lstrip("\u2192").strip()
            entries.append((s.lstrip("*").strip(), reason))
    return entries


def run_dogwatch(plans, *, dogs_path, report_path, reist_bald, on_progress=None,
                 workers=DEFAULT_WORKERS, **run_kwargs):
    """Check all online dogs, write the GEÄNDERT section of every healthy
    category and return a Summary. Blocking - call it from a worker thread.

    run_kwargs go to dogwatch.run (tests pass fake network functions).
    """
    pairs = build_dog_refs(plans, dogs_path, reist_bald)
    refs = [ref for _, ref in pairs]
    gender_of = {ref.key: gender for gender, ref in pairs}

    os.makedirs(report_path, exist_ok=True)
    store = Store(os.path.join(report_path, DB_NAME))
    try:
        result = run(refs, store, workers=workers, on_progress=on_progress, **run_kwargs)
    finally:
        store.close()

    changed = {p.gender: {} for p in plans if not p.error and p.doglist is not None}
    for f in result.findings:
        changed[gender_of[f.dog.key]].setdefault(f.dog.name, []).append(reason_for(f))
    for gender, entries in changed.items():
        write_changed_section(report_path, gender, entries)

    return Summary(
        changed=changed,
        n_changed=sum(len(v) for v in changed.values()),
        checked=result.checked, baselined=result.baselined, cached=result.cached,
        warnings=[f"{f.dog.key}: {f.detail}" for f in result.warnings],
        errors=[f"{f.dog.key}: {f.detail}" for f in result.errors],
        seconds=result.seconds)

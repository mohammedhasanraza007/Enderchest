"""The ownership-check measurement (Phase 6 spec, gate 1; D-115).

Runs the real check on the owner's 20 photos against a COPY of the newest backup of the owner's
inventory, offline, and writes the gate-1 table: for each photo the top candidate, its level and
whether it is right. An owned photo (`owned-NN-name.jpg`) is right when its item (the `public_id`
in `labels.csv`) is the top candidate; a not-owned photo (`not-owned-NN-name.jpg`) is right when
no candidate is High. A false High on a not-owned photo is a major defect (spec).

The backup file and its photo mirror are only read: the database is copied into a temporary
folder and every write (embeddings, migrations) lands in the copy. Only real photos count (D-056).

  python scripts/ownership_measure.py --backups DIR --photos DIR --out DIR [--model FILE]

`labels.csv` columns: `file,public_id` (blank `public_id` for a not-owned photo). `--model` takes
another ONNX image model with the same input and output (D-115's comparison).
"""

import argparse
import csv
import shutil
import sqlite3
import statistics
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path

from app.backup.catalog import list_backups
from app.config import Settings
from app.db import migrate
from app.services import embeddings, ownership

USER_ID = 1


def newest_backup(folder: Path) -> Path:
    entries = list_backups(folder)
    if not entries:
        sys.exit(f"No backup in {folder}: run backup.bat (or Back up now) first.")
    return folder / f"{entries[0].name}.sqlite3"


def copy_inventory(backups: Path, work: Path, model: Path | None) -> tuple[Settings, Path]:
    source = newest_backup(backups)
    data = work / "data"
    (data / "db").mkdir(parents=True)
    shutil.copyfile(source, data / "db" / "enderchest.sqlite3")
    (data / "photos").symlink_to(backups / "photos", target_is_directory=True)
    (data / "upload-tmp").mkdir()
    settings = Settings(env="test", port=8470, data_dir=data, backups_dir=work / "none",
                        backup_dir_hint="")
    if model is not None:
        settings = replace(settings, embedding_model=model)
    return settings, source


def connect(settings: Settings) -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    migrate.migrate(conn)  # an older backup moves to the current schema, in the copy only
    return conn


def measure(args: argparse.Namespace) -> int:
    labels = {row["file"]: (row.get("public_id") or "").strip()
              for row in csv.DictReader((args.photos / "labels.csv").open(encoding="utf-8"))}
    with tempfile.TemporaryDirectory() as folder:
        settings, source = copy_inventory(args.backups, Path(folder), args.model)
        conn = connect(settings)
        while embeddings.fill(conn, settings, USER_ID, limit=32):
            pass
        rows, times = [], []
        for name in sorted(labels):
            started = time.perf_counter()
            answer = ownership.check(conn, settings, USER_ID, (args.photos / name).read_bytes(),
                                     None)
            times.append((time.perf_counter() - started) * 1000)
            top = answer["candidates"][0] if answer["candidates"] else None
            owned = name.startswith("owned-")
            expected = labels[name]
            if owned:
                right = top is not None and top["public_id"] == expected
            else:
                right = not any(c["level"] == "high" for c in answer["candidates"])
            false_high = not owned and not right
            rows.append([name, expected or "(not owned)", top["public_id"] if top else "",
                         top["name"] if top else "", top["level"] if top else "",
                         "; ".join(top["reasons"]) if top else "",
                         "yes" if right else ("NO: false High (major)" if false_high else "NO")])
        conn.close()
    args.out.mkdir(parents=True, exist_ok=True)
    table = args.out / "ownership-results.md"
    owned_right = sum(r[6] == "yes" for r in rows if r[0].startswith("owned-"))
    false_highs = sum(r[6].startswith("NO: false High") for r in rows)
    lines = [f"# Ownership check, gate 1 ({time.strftime('%Y-%m-%d %H:%M')})", "",
             f"Inventory: a copy of `{source.name}`; model `{settings.embedding_model.name}`.",
             f"Owned top-1 right: {owned_right} of {sum(r[0].startswith('owned-') for r in rows)};"
             f" false High on not-owned: {false_highs}; median "
             f"{statistics.median(times):.0f} ms per photo.", "",
             "| Photo | Expected | Top candidate | Name | Level | Reasons | Right |",
             "|---|---|---|---|---|---|---|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    table.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if false_highs else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--backups", type=Path, required=True)
    parser.add_argument("--photos", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", type=Path)
    return measure(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())

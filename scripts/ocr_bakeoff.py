"""The OCR engine bake-off (Phase 3 spec, Build 1; D-062, D-063, D-099).

Runs each candidate engine on the owner's photos at long edges 1024 and 1600 and writes the
table the spec asks for: per field (name tokens, model, size, expiry date) correct / partial /
wrong against the owner's confirmed `labels.csv`, median and p95 latency, peak memory, the image
size fed to the engine, and the weighted accuracy (expiry x3, model x2, name x1, size x1). The
choice is the most accurate engine whose median latency is at most 4 s. Every reading goes
through the app's own field extraction (`app.services.extraction.propose`), so the engines are
compared on what the owner would actually see.

Only real photos count (D-056): run it on `tests/fixtures/private/phase3/` after the owner has
confirmed `labels.csv`. The `bakeoff` image target holds all four engines (`test.bat bakeoff`);
the app image holds RapidOCR only, so elsewhere the other engines report "not installed".

  python scripts/ocr_bakeoff.py --photos DIR --out DIR [--engines rapidocr,tesseract,...]
  python scripts/ocr_bakeoff.py --warm     download the engines' models now (image build time)
"""

import argparse
import csv
import json
import math
import re
import resource
import shutil
import statistics
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

ENGINES = ("rapidocr", "easyocr", "doctr", "tesseract")
EDGES = (1024, 1600)
WEIGHTS = {"expiry": 3, "model": 2, "name": 1, "size": 1}
MAX_MEDIAN_MS = 4000
THREADS = 4
PHOTO_TYPES = {".jpg", ".jpeg", ".png", ".webp"}


# ---- engines (each runs in its own child process, so its memory is measured alone) ----------

def _rapidocr():
    from app.integrations.ocr import engine

    def read(image):
        return [(raw.text, raw.confidence, raw.points) for raw in engine.recognise(image, THREADS)]
    return read


def _easyocr():
    import easyocr
    import numpy

    reader = easyocr.Reader(["en"], gpu=False, verbose=False)

    def read(image):
        return [(text, float(score), tuple((float(x), float(y)) for x, y in box))
                for box, text, score in reader.readtext(numpy.array(image))]
    return read


def _doctr():
    import numpy
    from onnxtr.models import ocr_predictor

    predictor = ocr_predictor()

    def read(image):
        width, height = image.size
        found = []
        for block in predictor([numpy.array(image)]).pages[0].blocks:
            for line in block.lines:
                (x0, y0), (x1, y1) = line.geometry
                text = " ".join(word.value for word in line.words)
                score = statistics.mean(word.confidence for word in line.words)
                found.append((text, float(score), ((x0 * width, y0 * height),
                                                   (x1 * width, y0 * height),
                                                   (x1 * width, y1 * height),
                                                   (x0 * width, y1 * height))))
        return found
    return read


def _tesseract():
    if shutil.which("tesseract") is None:
        raise FileNotFoundError("tesseract")

    def read(image):
        rows = subprocess.run(["tesseract", "stdin", "stdout", "-l", "eng", "--psm", "11", "tsv"],
                              input=_png(image), capture_output=True, check=True).stdout
        lines: dict[tuple, list] = {}
        for row in csv.DictReader(rows.decode().splitlines(), delimiter="\t",
                                  quoting=csv.QUOTE_NONE):
            if row["text"] and row["text"].strip() and float(row["conf"]) >= 0:
                key = (row["block_num"], row["par_num"], row["line_num"])
                lines.setdefault(key, []).append(row)
        found = []
        for words in lines.values():
            x0 = min(int(w["left"]) for w in words)
            y0 = min(int(w["top"]) for w in words)
            x1 = max(int(w["left"]) + int(w["width"]) for w in words)
            y1 = max(int(w["top"]) + int(w["height"]) for w in words)
            found.append((" ".join(w["text"] for w in words),
                          statistics.mean(float(w["conf"]) for w in words) / 100,
                          ((x0, y0), (x1, y0), (x1, y1), (x0, y1))))
        return found
    return read


def _png(image) -> bytes:
    import io

    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


LOADERS = {"rapidocr": _rapidocr, "easyocr": _easyocr, "doctr": _doctr, "tesseract": _tesseract}


def child(engine: str, edge: int, photos: list[Path]) -> dict:
    """One engine at one edge on every photo; prints JSON for the parent."""
    from PIL import Image

    try:
        read = LOADERS[engine]()
    except (ImportError, FileNotFoundError) as missing:
        return {"missing": f"not installed ({missing.__class__.__name__})"}
    results = []
    for path in photos:
        with Image.open(path) as opened:
            image = opened.convert("RGB")
        image.thumbnail((edge, edge), Image.Resampling.LANCZOS)
        started = time.perf_counter()
        try:
            raw = read(image)
            error = None
        except Exception as failed:  # one bad photo must not end the measurement
            raw, error = [], f"{failed.__class__.__name__}: {failed}"
        results.append({"file": path.name, "ms": (time.perf_counter() - started) * 1000,
                        "pixels": image.size[0] * image.size[1], "error": error,
                        "lines": [[text, score, [list(p) for p in points]]
                                  for text, score, points in raw]})
    peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    return {"photos": results, "peak_mb": round(peak_mb)}


# ---- scoring ---------------------------------------------------------------------------------

def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.casefold()))


def _bare(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def score_photo(label: dict, lines: list, today: date) -> dict[str, str]:
    """correct / partial / wrong per labelled field (model and size only when labelled)."""
    from app.integrations.ocr.pipeline import Line
    from app.services.extraction import propose

    parsed = []
    for text, confidence, points in lines:
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = points
        height = (math.dist((x0, y0), (x3, y3)) + math.dist((x1, y1), (x2, y2))) / 2
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        parsed.append(Line(" ".join(text.split()), confidence,
                           (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))), height, 0))
    proposed = propose(parsed, today)["proposed"]
    value = {field: str(p["value"]) for field, p in proposed.items()}
    raw = " ".join(line.text for line in parsed)
    marks: dict[str, str] = {}

    wanted = _tokens(label["name"])
    hit = len(wanted & _tokens(value.get("name", ""))) / max(1, len(wanted))
    marks["name"] = "correct" if hit == 1 else "partial" if hit >= 0.5 else "wrong"
    if label["model"].strip():
        marks["model"] = ("correct" if _bare(value.get("model", "")) == _bare(label["model"])
                          else "partial" if _bare(label["model"]) in _bare(raw) else "wrong")
    if label["size"].strip():
        want = label["size"].casefold().replace(" ", "")
        got = value.get("size", "").casefold().replace(" ", "")
        number = re.match(r"[\d.,/]+", want)
        marks["size"] = ("correct" if got == want
                         else "partial" if number and number.group() in got else "wrong")
    expected = label["expiry_date"].strip()
    alternatives = proposed.get("expiry_date", {}).get("alternatives") or []
    if not expected:
        marks["expiry"] = "correct" if "expiry_date" not in value else "wrong"
    else:
        marks["expiry"] = ("correct" if value.get("expiry_date") == expected
                           else "partial" if expected in alternatives else "wrong")
    return marks


def summarise(engine: str, edge: int, run: dict, labels: dict[str, dict], today: date) -> dict:
    if "missing" in run:
        return {"engine": engine, "edge": edge, "missing": run["missing"]}
    counts = {field: {"correct": 0, "partial": 0, "wrong": 0} for field in WEIGHTS}
    for photo in run["photos"]:
        for field, mark in score_photo(labels[photo["file"]], photo["lines"], today).items():
            counts[field][mark] += 1
    earned = total = 0.0
    for field, weight in WEIGHTS.items():
        tally = counts[field]
        earned += weight * (tally["correct"] + 0.5 * tally["partial"])
        total += weight * sum(tally.values())
    times = sorted(photo["ms"] for photo in run["photos"])
    p95 = times[max(0, math.ceil(0.95 * len(times)) - 1)] if times else 0
    return {
        "engine": engine, "edge": edge, "fields": counts,
        "weighted": round(earned / total, 3) if total else 0.0,
        "median_ms": round(statistics.median(times)) if times else 0, "p95_ms": round(p95),
        "peak_mb": run["peak_mb"],
        "megapixels": round(statistics.mean(p["pixels"] for p in run["photos"]) / 1e6, 2),
        "errors": [p["file"] for p in run["photos"] if p["error"]],
    }


def table(rows: list[dict]) -> str:
    out = ["| Engine | Edge | Name c/p/w | Model c/p/w | Size c/p/w | Expiry c/p/w | Weighted | "
           "Median ms | p95 ms | Peak MB | MP |", "|" + "---|" * 11]
    for row in rows:
        if "missing" in row:
            out.append(f"| {row['engine']} | {row['edge']} | {row['missing']} |" + " |" * 9)
            continue
        cells = ["/".join(str(row["fields"][f][k]) for k in ("correct", "partial", "wrong"))
                 for f in ("name", "model", "size", "expiry")]
        out.append(f"| {row['engine']} | {row['edge']} | " + " | ".join(cells)
                   + f" | {row['weighted']:.3f} | {row['median_ms']} | {row['p95_ms']} | "
                   f"{row['peak_mb']} | {row['megapixels']} |")
    return "\n".join(out)


def choose(rows: list[dict]) -> dict | None:
    fit = [row for row in rows if "missing" not in row and row["median_ms"] <= MAX_MEDIAN_MS]
    return max(fit, key=lambda row: (row["weighted"], -row["median_ms"]), default=None)


def load_labels(folder: Path) -> dict[str, dict]:
    with open(folder / "labels.csv", newline="", encoding="utf-8") as handle:
        return {row["file"]: row for row in csv.DictReader(handle)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--photos", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--engines", default=",".join(ENGINES))
    parser.add_argument("--edges", default=",".join(map(str, EDGES)))
    parser.add_argument("--child", nargs=2, metavar=("ENGINE", "EDGE"))
    parser.add_argument("--warm", action="store_true")
    args = parser.parse_args()

    if args.warm:
        for engine in ENGINES:
            try:
                LOADERS[engine]()
                print(f"{engine}: ready")
            except (ImportError, FileNotFoundError) as missing:
                print(f"{engine}: not installed ({missing.__class__.__name__})")
        return 0
    labels = load_labels(args.photos)
    photos = sorted(p for p in args.photos.iterdir()
                    if p.suffix.lower() in PHOTO_TYPES and p.name in labels)
    if args.child:
        print(json.dumps(child(args.child[0], int(args.child[1]), photos)))
        return 0
    if not photos:
        print(f"No labelled photos in {args.photos}: the measurement needs the owner's photos.")
        return 2
    today = date.today()
    rows = []
    for engine in args.engines.split(","):
        for edge in map(int, args.edges.split(",")):
            done = subprocess.run([sys.executable, __file__, "--photos", str(args.photos),
                                   "--child", engine, str(edge)], capture_output=True, text=True)
            run = (json.loads(done.stdout.strip().splitlines()[-1]) if done.returncode == 0
                   else {"missing": f"failed: {done.stderr.strip().splitlines()[-1:]}"})
            rows.append(summarise(engine, edge, run, labels, today))
            print(f"{engine} at {edge}: done", file=sys.stderr)
    chosen = choose(rows)
    report = (f"OCR bake-off on {len(photos)} photos, {today.isoformat()}\n\n{table(rows)}\n\n"
              + (f"Choice: {chosen['engine']} at {chosen['edge']} px (weighted "
                 f"{chosen['weighted']:.3f}, median {chosen['median_ms']} ms)."
                 if chosen else "No engine met the 4 s median latency rule."))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "bakeoff.md").write_text(report + "\n", encoding="utf-8")
    (args.out / "bakeoff.json").write_text(json.dumps({"rows": rows, "choice": chosen}, indent=2),
                                           encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())

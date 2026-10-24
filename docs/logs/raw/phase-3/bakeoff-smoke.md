> Smoke test of the harness on two labels drawn by Pillow, in the tools image (RapidOCR only installed): proves the script runs and scores; NOT gate evidence (D-056). The real measurement needs the owner's 20 photos (gate 2 BLOCKED).

OCR bake-off on 2 photos, 2026-10-24

| Engine | Edge | Name c/p/w | Model c/p/w | Size c/p/w | Expiry c/p/w | Weighted | Median ms | p95 ms | Peak MB | MP |
|---|---|---|---|---|---|---|---|---|---|---|
| rapidocr | 1024 | 2/0/0 | 2/0/0 | 2/0/0 | 2/0/0 | 1.000 | 860 | 1379 | 503 | 0.52 |
| rapidocr | 1600 | 2/0/0 | 2/0/0 | 2/0/0 | 2/0/0 | 1.000 | 980 | 1562 | 569 | 1.28 |
| tesseract | 1024 | not installed (FileNotFoundError) | | | | | | | | | |
| tesseract | 1600 | not installed (FileNotFoundError) | | | | | | | | | |

Choice: rapidocr at 1024 px (weighted 1.000, median 860 ms).

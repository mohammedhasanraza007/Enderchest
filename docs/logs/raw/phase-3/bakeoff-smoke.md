> Smoke test of the harness and the `bakeoff` image on two labels drawn by Pillow, run with `--network none` (all four engines loaded offline; models baked in at build). It proves the tooling works; it is NOT gate evidence and says nothing about real packs (D-056). The real measurement needs the owner's 20 photos (gate 2 BLOCKED).

OCR bake-off on 2 photos, 2026-10-24

| Engine | Edge | Name c/p/w | Model c/p/w | Size c/p/w | Expiry c/p/w | Weighted | Median ms | p95 ms | Peak MB | MP |
|---|---|---|---|---|---|---|---|---|---|---|
| rapidocr | 1024 | 2/0/0 | 2/0/0 | 2/0/0 | 2/0/0 | 1.000 | 951 | 1628 | 509 | 0.52 |
| rapidocr | 1600 | 2/0/0 | 2/0/0 | 2/0/0 | 2/0/0 | 1.000 | 764 | 1197 | 562 | 1.28 |
| easyocr | 1024 | 2/0/0 | 1/0/1 | 2/0/0 | 2/0/0 | 0.857 | 1864 | 2019 | 1067 | 0.52 |
| easyocr | 1600 | 2/0/0 | 1/0/1 | 2/0/0 | 2/0/0 | 0.857 | 4317 | 4585 | 1517 | 1.28 |
| doctr | 1024 | 2/0/0 | 1/1/0 | 2/0/0 | 2/0/0 | 0.929 | 830 | 862 | 1258 | 0.52 |
| doctr | 1600 | 2/0/0 | 1/1/0 | 2/0/0 | 2/0/0 | 0.929 | 722 | 734 | 1279 | 1.28 |
| tesseract | 1024 | 2/0/0 | 1/0/1 | 2/0/0 | 2/0/0 | 0.857 | 174 | 204 | 43 | 0.52 |
| tesseract | 1600 | 2/0/0 | 1/0/1 | 2/0/0 | 2/0/0 | 0.857 | 189 | 198 | 48 | 1.28 |

Choice: rapidocr at 1600 px (weighted 1.000, median 764 ms).

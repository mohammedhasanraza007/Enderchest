"""Proposals from read lines (Phase 3 spec, Build 4): name, model or part number, size, expiry."""

from datetime import date

from app.integrations.ocr.pipeline import Line
from app.services.extraction import propose

TODAY = date(2026, 10, 17)


def lines(*rows: tuple[str, float, float]) -> list[Line]:
    """Rows of (text, confidence, text height), top to bottom on one photo."""
    return [Line(text, confidence, (0, 40 * n, 400, 40 * n + int(height)), height, 0)
            for n, (text, confidence, height) in enumerate(rows)]


LABEL = lines(("OAT MILK BARISTA", 0.99, 60), ("1 L  MODEL AB-1234X", 0.95, 30),
              ("MFD 12/01/2026  EXP 14/03/2027", 0.97, 30), ("BATCH L4471  Net Qty 500 ml", 0.99, 30))


def test_a_label_gives_all_four_fields():
    proposed = propose(LABEL, TODAY)["proposed"]
    assert proposed["name"]["value"] == "Oat Milk Barista"
    assert proposed["model"]["value"] == "AB-1234X"
    assert proposed["size"]["value"] == "500 ml"  # the net quantity line wins
    assert proposed["expiry_date"]["value"] == "2027-03-14"
    assert {p["source"] for p in proposed.values()} == {"ocr"}


def test_values_say_where_they_came_from():
    proposed = propose(LABEL, TODAY)["proposed"]
    assert proposed["expiry_date"]["text"] == "EXP 14/03/2027"
    assert proposed["model"]["text"] == "1 L MODEL AB-1234X"


def test_confidence_follows_labels_and_reading_quality():
    proposed = propose(LABEL, TODAY)["proposed"]
    assert proposed["model"]["confidence"] == "high"  # after "MODEL"
    assert proposed["expiry_date"]["confidence"] == "high"  # after "EXP", nothing flagged
    assert proposed["name"]["confidence"] == "high"  # biggest print by far, read cleanly


def test_a_batch_code_a_size_and_a_date_are_never_the_model():
    proposed = propose(lines(("LOT L4471 500ML 2027-03-14", 0.99, 30)), TODAY)["proposed"]
    assert "model" not in proposed


def test_an_unlabelled_model_is_offered_with_less_confidence():
    proposed = propose(lines(("Relay module", 0.98, 50), ("SRD-05VDC-SL-C", 0.97, 25)),
                       TODAY)["proposed"]
    assert proposed["model"]["value"] == "SRD-05VDC-SL-C"
    assert proposed["model"]["confidence"] == "medium"


def test_sizes_take_their_unit():
    for text, size in [("Drill bit 6 mm", "6 mm"), ("Charger 5V 2A", "5 V"), ('Monitor 24"', '24"'),
                       ("Power bank 10000 mAh", "10000 mAh"), ("Tray 30 x 20 cm", "30 x 20 cm"),
                       ("Screws 12 pcs", "12 pcs")]:
        assert propose(lines((text, 0.99, 30)), TODAY)["proposed"]["size"]["value"] == size


def test_months_of_shelf_life_are_not_a_size():
    proposed = propose(lines(("BEST BEFORE 6 MONTHS FROM MFG", 0.99, 30)), TODAY)["proposed"]
    assert "size" not in proposed


def test_the_name_skips_dates_sizes_and_boilerplate():
    proposed = propose(lines(("EXP 14 MAR 2027", 0.99, 80), ("Net Wt 200 g", 0.99, 70),
                             ("Ingredients: oats, water", 0.99, 60), ("Rolled Oats", 0.9, 40)),
                       TODAY)["proposed"]
    assert proposed["name"]["value"] == "Rolled Oats"


def test_an_ambiguous_expiry_keeps_both_readings():
    proposed = propose(lines(("EXP 03/04/2027", 0.99, 30)), TODAY)["proposed"]["expiry_date"]
    assert proposed["value"] == "2027-04-03"
    assert proposed["alternatives"] == ["2027-03-04"]
    assert proposed["flags"] == ["ambiguous"]
    assert proposed["confidence"] == "low"


def test_a_month_only_expiry_is_medium():
    proposed = propose(lines(("EXP 03/2027", 0.99, 30)), TODAY)["proposed"]["expiry_date"]
    assert (proposed["value"], proposed["confidence"]) == ("2027-03-31", "medium")


def test_a_manufacture_date_alone_is_a_note_not_an_expiry():
    result = propose(lines(("Packed on 05 JUN 2026", 0.99, 30)), TODAY)
    assert "expiry_date" not in result["proposed"]
    assert result["notes"] == ["Only a manufacture or packing date was found (Packed on 05 JUN "
                               "2026); it is never used as the expiry."]


def test_a_blurry_reading_lowers_confidence():
    proposed = propose(lines(("Oat Milk", 0.6, 60), ("EXP 14/03/2027", 0.6, 30)), TODAY)
    assert proposed["proposed"]["name"]["confidence"] == "low"
    assert proposed["proposed"]["expiry_date"]["confidence"] == "low"


def test_no_text_says_so():
    assert propose([], TODAY) == {"proposed": {}, "notes": ["No text was found in the photo."]}

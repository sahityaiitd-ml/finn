from app.results_view import build_view


def row(status="ok", ok=(True, True, True)):
    return {
        "status": status,
        "basis": "consolidated",
        "flags": [],
        "parsed": {
            "status": status, "page": 8, "reason": "", "column_ok": list(ok),
            "metrics": {
                "revenue": {"values": [110.0, 100.0, 80.0], "page": 8, "line": "Rev 110 100 80"},
                "pbt": {"values": [20.0, 10.0, 25.0], "page": 8, "line": "PBT 20 10 25"},
                "pat": {"values": [15.0, 8.0, 20.0], "page": 8, "line": "PAT 15 8 20"},
            },
            "derived": {"ebitda": [30.0, 25.0, 28.0], "exceptional": [-5.0, 0, 0]},
        },
    }  # fmt: skip


def test_changes_are_computed_in_python_and_cite_a_page():
    v = build_view("X", "X Ltd", "2026-09", "abc", row())
    rev = next(r for r in v["rows"] if r["key"] == "revenue")
    assert rev["qoq_pct"] == 10.0 and rev["yoy_pct"] == 37.5 and rev["page"] == 8
    assert all(r["page"] == 8 for r in v["rows"])  # no number without a source
    assert v["exceptional"]["value"] == -5.0


def test_failed_column_is_unavailable_not_guessed():
    v = build_view("X", "X Ltd", "2026-09", "abc", row(ok=(True, True, False)))
    rev = next(r for r in v["rows"] if r["key"] == "revenue")
    assert rev["yoy_pct"] is None and rev["yoy_available"] is False and rev["qoq_pct"] == 10.0


def test_see_pdf_has_no_numbers():
    v = build_view("X", "X Ltd", "2026-09", "abc", row(status="see_pdf", ok=(False,) * 3))
    assert v["rows"] == [] and v["message"] == "See PDF"

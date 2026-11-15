from datetime import date, datetime, timedelta

from extract.eod import (
    FILING_FOUND,
    IST,
    NO_FILING,
    Bar,
    cause_label,
    dry_run,
    evaluate,
)


def bars(n=25, vol=1000, close=100.0, last_vol=None, last_close=None):
    out = []
    d = date(2026, 10, 1)
    for i in range(n):
        out.append(Bar("X", d + timedelta(days=i), close, vol))
    if last_vol is not None or last_close is not None:
        b = out[-1]
        out[-1] = Bar("X", b.d, last_close if last_close is not None else b.close,
                      last_vol if last_vol is not None else b.volume)  # fmt: skip
    return out


def test_volume_rule_is_strictly_above_the_multiple_of_the_20_day_average():
    assert evaluate("X", bars(last_vol=2000), 2.0, 5.0) is None  # exactly 2x: not above
    a = evaluate("X", bars(last_vol=2100), 2.0, 5.0)
    assert a["triggered"] == ["volume"] and a["ratio"] == 2.1 and a["avg_volume_20d"] == 1000


def test_price_rule_uses_absolute_move_both_directions():
    up = evaluate("X", bars(last_close=106), 2.0, 5.0)
    down = evaluate("X", bars(last_close=94), 2.0, 5.0)
    assert up["triggered"] == ["price"] and up["pct"] == 6.0
    assert down["triggered"] == ["price"] and down["pct"] == -6.0
    assert evaluate("X", bars(last_close=104), 2.0, 5.0) is None


def test_both_rules_and_thresholds_of_zero_turn_a_rule_off():
    a = evaluate("X", bars(last_vol=5000, last_close=90), 2.0, 5.0)
    assert a["triggered"] == ["volume", "price"]
    assert evaluate("X", bars(last_vol=5000, last_close=90), 0, 5.0)["triggered"] == ["price"]
    assert evaluate("X", bars(last_vol=5000, last_close=90), 2.0, 0)["triggered"] == ["volume"]
    assert evaluate("X", bars(last_vol=5000, last_close=90), 0, 0) is None


def test_not_enough_history_means_no_alert_not_a_guess():
    assert evaluate("X", bars(n=10, last_vol=9000), 2.0, 5.0) is None


def test_the_current_session_is_excluded_from_its_own_average():
    b = bars(last_vol=3000)
    assert evaluate("X", b, 2.0, 5.0)["avg_volume_20d"] == 1000


# ---------- cause label: exactly two strings, never a guess ----------
D, PREV = date(2026, 11, 13), date(2026, 11, 12)


def filing(ts, floor=False, mat=10):
    return {"published_at": ts.isoformat(), "never_collapse": floor, "materiality": mat, "id": "f"}


def at(day, h, m=0):
    return datetime(day.year, day.month, day.day, h, m, tzinfo=IST)


def test_label_is_one_of_exactly_two_strings():
    assert {NO_FILING, FILING_FOUND} == {
        "No related filing found",
        "Related filing found, cause unconfirmed",
    }
    assert cause_label(D, PREV, [])[0] == NO_FILING


def test_a_material_filing_between_the_closes_is_related():
    label, found = cause_label(D, PREV, [filing(at(PREV, 18, 40), floor=True)])
    assert label == FILING_FOUND and len(found) == 1
    label, _ = cause_label(D, PREV, [filing(at(D, 11, 5), mat=60)])
    assert label == FILING_FOUND


def test_routine_filings_and_filings_outside_the_window_are_not_related():
    assert cause_label(D, PREV, [filing(at(D, 11), mat=5)])[0] == NO_FILING  # routine ESOP etc.
    assert (
        cause_label(D, PREV, [filing(at(PREV, 14), floor=True)])[0] == NO_FILING
    )  # before prev close
    assert cause_label(D, PREV, [filing(at(D, 17), floor=True)])[0] == NO_FILING  # after this close


# ---------- dry run ----------
def test_dry_run_counts_alerts_and_those_with_a_related_filing():
    b = bars(n=30, vol=1000)
    b[-3] = Bar("X", b[-3].d, 100.0, 5000)  # volume spike
    b[-1] = Bar("X", b[-1].d, 110.0, 1000)  # price spike
    f = {
        "X": [
            filing(datetime.combine(b[-1].d, datetime.min.time(), IST).replace(hour=10), floor=True)
        ]
    }
    r = dry_run({"X": b}, f, {"X": (2.0, 5.0)})
    assert r["alerts"] >= 2 and r["with_filing"] == 1
    off = dry_run({"X": b}, f, {"X": (0.0, 0.0)})
    assert off["alerts"] == 0


def test_load_bars_pages_past_the_api_row_cap():
    from jobs.eod import load_bars

    rows = [
        {"symbol": "X", "d": f"2026-01-{(i % 28) + 1:02d}", "close": 1, "volume": 1}
        for i in range(1500)
    ]

    class Q:
        def __init__(self):
            self.lo = 0
            self.hi = 0

        def select(self, *_):
            return self

        def in_(self, *_):
            return self

        def order(self, *_):
            return self

        def range(self, lo, hi):
            self.lo, self.hi = lo, hi
            return self

        def execute(self):
            return type("R", (), {"data": rows[self.lo : self.hi + 1]})

    class DB:
        def table(self, _):
            return Q()

    assert len(load_bars(DB(), ["X"])["X"]) == 1500  # not truncated at 1000

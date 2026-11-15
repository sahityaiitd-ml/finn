import pandas as pd

from extract.eod import avg_volume_20d, bars_from_frame


def test_avg_volume_excludes_latest_and_needs_20():
    assert avg_volume_20d([100] * 21 + [999]) == 100
    assert avg_volume_20d([100] * 10) is None


def test_bars_from_frame():
    idx = pd.to_datetime(["2026-11-12", "2026-11-13"])
    cols = pd.MultiIndex.from_product([["TCS.NS"], ["Close", "Volume"]])
    df = pd.DataFrame([[100.0, 10], [None, None]], index=idx, columns=cols)
    out = bars_from_frame(df, ["TCS", "XYZ"], ".NS")
    assert [b.close for b in out["TCS"]] == [100.0]
    assert "XYZ" not in out

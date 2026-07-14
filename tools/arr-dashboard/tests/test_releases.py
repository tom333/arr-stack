from arr_dashboard.releases import parse_release_title


def test_parse_web_1080p_x265_french():
    p = parse_release_title("Bubble.2022.FRENCH.1080p.NF.WEB.AV1.DDP.5.1-Niroma")
    assert p["year"] == 2022
    assert p["resolution"] == "1080p"
    assert p["source"] == "WEB"
    assert p["language"] == "FRENCH"


def test_parse_bluray_x265_multi():
    p = parse_release_title("Mortal.Engines.2018.MULTI.VFF.1080p.BluRay.x265-mHDgz")
    assert p["resolution"] == "1080p"
    assert p["source"] == "BluRay"
    assert p["codec"] == "x265"
    assert p["language"] == "MULTI"


def test_parse_unknown_bits_are_none():
    p = parse_release_title("Some Movie Title")
    assert p["year"] is None and p["resolution"] is None and p["source"] is None

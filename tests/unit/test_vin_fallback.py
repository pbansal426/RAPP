from backend.vin_fallback import wmi_fallback_decode


def test_unknown_wmi_returns_none():
    assert wmi_fallback_decode("WVWZZZ1JZXW000001") is None


def test_known_wmi_decodes_make_and_year_only():
    # 1HG = Honda; position 7 ('1') is numeric so the 1980s+ cycle applies,
    # position 10 ('M') is offset 11 in that cycle -> 1991.
    result = wmi_fallback_decode("1HGBH41JXMN109186")
    assert result is not None
    assert result["make"] == "HONDA"
    assert result["year"] == 1991
    assert result["model"] == ""
    assert result["decode_source"] == "offline_fallback"


def test_known_wmi_2010s_cycle():
    # 1NX = Toyota (NUMMI); position 7 ('E') is alphabetic so the 2010s+
    # cycle applies, position 10 ('A') is offset 0 -> 2010.
    result = wmi_fallback_decode("1NXBU4EE4AZ361925")
    assert result is not None
    assert result["make"] == "TOYOTA"
    assert result["year"] == 2010

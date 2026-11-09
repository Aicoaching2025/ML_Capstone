"""Offline tests for the Step 7 download helpers (no network)."""
import json
import zipfile

from acquisition import download as d


def test_months_inclusive_across_years():
    m = d.months("2017-12", "2018-02")
    assert m == ["201712", "201801", "201802"]
    assert len(d.months("2017-01", "2025-12")) == 108


def test_validators(tmp_path):
    z = tmp_path / "a.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("x.csv", "a,b\n1,2\n")
    bad = tmp_path / "b.zip"
    bad.write_text("<html>not a zip</html>")
    assert d.valid_zip(z) and not d.valid_zip(bad)
    good = tmp_path / "om.json"
    good.write_text(json.dumps({"hourly": {"time": ["2024-01-01T00:00"]}}))
    err = tmp_path / "err.json"
    err.write_text(json.dumps({"error": True, "reason": "rate limit"}))
    assert d.valid_openmeteo_json(good) and not d.valid_openmeteo_json(err)


def test_existing_valid_file_is_skipped_and_manifest_dedupes(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "ROOT", tmp_path)
    monkeypatch.setattr(d, "MANIFEST", tmp_path / "downloads.csv")
    f = tmp_path / "x.json"
    f.write_text(json.dumps({"hourly": {"time": ["t"]}}))
    meta = d.fetch("https://example.invalid/x", f, d.valid_openmeteo_json)  # no network used
    assert meta["skipped"] is True
    d.record(f, meta, provider="test")
    d.record(f, meta, provider="test")
    assert len(d.read_manifest()) == 1

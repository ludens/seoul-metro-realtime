from pathlib import Path

import pytest

from seoul_metro_realtime.station_lookup import find_station_candidates, load_station_rows, normalize_station_name


def test_normalize_station_name_trims_suffix_and_whitespace():
    assert normalize_station_name("  서울역  ") == "서울"


def test_normalize_station_name_applies_alias_map():
    assert normalize_station_name("공릉역") == "공릉(서울산업대입구)"


def test_find_station_candidates_returns_multiple_lines_for_duplicate_name():
    rows = [
        {"SUBWAY_ID": "1001", "STATN_ID": "1001000133", "STATN_NM": "청량리", "호선이름": "1호선"},
        {"SUBWAY_ID": "1063", "STATN_ID": "1063075310", "STATN_NM": "청량리", "호선이름": "경의중앙선"},
    ]

    result = find_station_candidates("청량리역", rows)

    assert [item["line_name"] for item in result] == ["1호선", "경의중앙선"]


def test_load_station_rows_parses_utf8_sig_csv(tmp_path: Path):
    csv_path = tmp_path / "stations.csv"
    csv_path.write_text(
        "SUBWAY_ID,STATN_ID,STATN_NM,호선이름\n1001,1001000133,서울,1호선\n",
        encoding="utf-8-sig",
    )

    rows = load_station_rows(csv_path)

    assert rows == [
        {
            "SUBWAY_ID": "1001",
            "STATN_ID": "1001000133",
            "STATN_NM": "서울",
            "호선이름": "1호선",
        }
    ]


def test_load_station_rows_rejects_missing_required_headers(tmp_path: Path):
    csv_path = tmp_path / "stations.csv"
    csv_path.write_text("SUBWAY_ID,STATN_ID,STATN_NM\n1001,1001000133,서울\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required headers: 호선이름"):
        load_station_rows(csv_path)

from __future__ import annotations

import csv
from pathlib import Path

REQUIRED_COLUMNS = ("SUBWAY_ID", "STATN_ID", "STATN_NM", "호선이름")

ALIAS_MAP = {
    "응암": "응암순환(상선)",
    "공릉": "공릉(서울산업대입구)",
    "남한산성입구": "남한산성입구(성남법원, 검찰청)",
    "대모산입구": "대모산",
    "천호": "천호(풍납토성)",
    "몽촌토성": "몽촌토성(평화의문)",
}


def normalize_station_name(raw_name: str) -> str:
    name = raw_name.strip()
    if name.endswith("역"):
        name = name[:-1]
    return ALIAS_MAP.get(name, name)


def find_station_candidates(raw_name: str, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized = normalize_station_name(raw_name)
    matches = [row for row in rows if row["STATN_NM"] == normalized or row["STATN_NM"] == raw_name.strip()]
    return [
        {
            "subway_id": row["SUBWAY_ID"],
            "station_id": row["STATN_ID"],
            "station_name": row["STATN_NM"],
            "line_name": row["호선이름"],
        }
        for row in matches
    ]


def _validate_required_columns(fieldnames: list[str] | None, csv_path: Path) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in (fieldnames or [])]
    if missing:
        raise ValueError(f"CSV {csv_path} is missing required headers: {', '.join(missing)}")


def load_station_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        _validate_required_columns(reader.fieldnames, csv_path)
        return list(reader)

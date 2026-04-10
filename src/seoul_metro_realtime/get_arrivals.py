from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import datetime
import json
from pathlib import Path
from typing import Callable
import os
import sys

import httpx
from dotenv import dotenv_values

from seoul_metro_realtime.station_lookup import normalize_station_name

LINE_NAME_BY_ID = {
    "1001": "1호선",
    "1002": "2호선",
    "1003": "3호선",
    "1004": "4호선",
    "1005": "5호선",
    "1006": "6호선",
    "1007": "7호선",
    "1008": "8호선",
    "1009": "9호선",
    "1061": "중앙선",
    "1063": "경의중앙선",
    "1065": "공항철도",
    "1067": "경춘선",
    "1075": "수인분당선",
    "1077": "신분당선",
    "1081": "경강선",
    "1092": "우이신설선",
    "1093": "서해선",
    "1032": "GTX-A",
}


@dataclass(frozen=True)
class Arrival:
    line_name: str
    train_line_nm: str
    seconds: int
    status: str
    is_last_train: bool
    receipt_time: str = ""
    arvl_msg2: str = ""
    arvl_cd: str = ""


def adjust_arrival_seconds(barvl_dt: int, receipt_time: str, now: datetime) -> int:
    received = datetime.fromisoformat(receipt_time)
    if received.tzinfo is None and now.tzinfo is not None:
        received = received.replace(tzinfo=now.tzinfo)
    delay_seconds = max(0, int((now - received).total_seconds()))
    return max(0, barvl_dt - delay_seconds)


def _clean_train_line_name(train_line_nm: str, status: str) -> str:
    cleaned = train_line_nm.strip()
    if status != "일반":
        cleaned = cleaned.replace(f" ({status})", "")
        cleaned = cleaned.replace(f"({status})", "")
    return cleaned.strip()


def _split_train_line_name(train_line_nm: str) -> tuple[str, str]:
    if " - " in train_line_nm:
        destination, direction = train_line_nm.split(" - ", 1)
        return destination.strip(), direction.strip()
    return train_line_nm.strip(), "기타"


def _format_arrival_eta(seconds: int, arvl_cd: str = "", arvl_msg2: str = "") -> str:
    if arvl_msg2:
        normalized_msg = arvl_msg2.strip()
        if "번째 전역" in normalized_msg or normalized_msg.endswith("후"):
            return normalized_msg
        if normalized_msg.endswith("도착") or normalized_msg.endswith("진입") or normalized_msg.endswith("출발"):
            return "곧 도착"

    if arvl_cd in {"0", "1", "2", "3", "4", "5"} and seconds <= 0:
        return "곧 도착"

    if seconds <= 0:
        return "운행중"

    minutes = seconds // 60
    if minutes <= 0:
        return "곧 도착"
    return f"{minutes}분 후 도착"


def _destination_and_direction(arrival: Arrival) -> tuple[str, str]:
    train_line_nm = _clean_train_line_name(arrival.train_line_nm, arrival.status)
    return _split_train_line_name(train_line_nm)


def _arrival_metadata(arrival: Arrival) -> str:
    suffix = []
    if arrival.status != "일반":
        suffix.append(arrival.status)
    if arrival.is_last_train:
        suffix.append("막차")
    return f" ({', '.join(suffix)})" if suffix else ""


def _normalize_arrivals(rows: list[dict[str, str]], now: datetime) -> list[Arrival]:
    parsed = parse_api_arrivals(rows)
    normalized = [
        replace(item, seconds=adjust_arrival_seconds(item.seconds, item.receipt_time, now))
        for item in parsed
    ]
    normalized.sort(key=lambda item: item.seconds)
    return normalized


def format_arrivals_summary(station_name: str, arrivals: list[Arrival]) -> str:
    grouped: dict[str, list[Arrival]] = defaultdict(list)
    for item in arrivals:
        grouped[item.line_name].append(item)

    lines = [f"{station_name} 실시간 도착정보", ""]
    for line_name, items in grouped.items():
        lines.append(line_name)
        direction_groups: dict[str, list[tuple[str, Arrival]]] = defaultdict(list)
        for item in items:
            destination, direction = _destination_and_direction(item)
            direction_groups[direction].append((destination, item))

        for direction, direction_items in direction_groups.items():
            lines.append(f"- {direction}")
            for destination, item in direction_items:
                seconds = max(0, item.seconds)
                eta = _format_arrival_eta(
                    seconds,
                    item.arvl_cd,
                    item.arvl_msg2,
                )
                lines.append(f"  - {destination}: {eta}{_arrival_metadata(item)}")
        lines.append("")
    return "\n".join(lines).strip()


def parse_api_arrivals(payload: list[dict[str, str]]) -> list[Arrival]:
    results = []
    for item in payload:
        results.append(
            Arrival(
                line_name=LINE_NAME_BY_ID.get(item["subwayId"], item["subwayId"]),
                train_line_nm=item.get("trainLineNm") or item.get("arvlMsg3") or "행선지 정보 없음",
                seconds=int(item.get("barvlDt") or 0),
                status=item.get("btrainSttus") or "일반",
                is_last_train=item.get("lstcarAt") == "1",
                receipt_time=item.get("recptnDt") or "",
                arvl_msg2=item.get("arvlMsg2") or "",
                arvl_cd=item.get("arvlCd") or "",
            )
        )
    return results


def extract_arrival_rows(payload: dict[str, object]) -> list[dict[str, str]]:
    if "realtimeArrivalList" in payload:
        return list(payload["realtimeArrivalList"])

    error = payload.get("errorMessage")
    if isinstance(error, dict) and error.get("code") == "INFO-200":
        return []

    if isinstance(error, dict):
        code = error.get("code", "UNKNOWN")
        message = error.get("message", "알 수 없는 오류")
        raise RuntimeError(f"{code}: {message}")

    raise RuntimeError("응답 형식을 해석할 수 없습니다.")


def build_summary_for_station(raw_name: str, rows: list[dict[str, str]], now: datetime) -> str:
    normalized = _normalize_arrivals(rows, now)
    return format_arrivals_summary(raw_name.removesuffix("역"), normalized)


def build_json_for_station(raw_name: str, rows: list[dict[str, str]], now: datetime) -> dict[str, object]:
    station_name = raw_name.removesuffix("역")
    arrivals = []
    for item in _normalize_arrivals(rows, now):
        destination, direction = _destination_and_direction(item)
        arrivals.append(
            {
                "line_name": item.line_name,
                "direction": direction,
                "destination": destination,
                "eta": _format_arrival_eta(item.seconds, item.arvl_cd, item.arvl_msg2),
                "seconds": item.seconds,
                "status": item.status,
                "is_last_train": item.is_last_train,
                "arvl_msg2": item.arvl_msg2,
                "arvl_cd": item.arvl_cd,
            }
        )
    return {
        "station_name": station_name,
        "generated_at": now.isoformat(),
        "arrivals": arrivals,
    }


def load_api_key(candidate_env_files: list[Path]) -> str:
    existing_key = os.getenv("SEOUL_OPEN_API_KEY")
    if existing_key:
        return existing_key

    for env_file in candidate_env_files:
        if env_file.exists():
            key = dotenv_values(env_file).get("SEOUL_OPEN_API_KEY")
            if key:
                return str(key)
    raise RuntimeError("SEOUL_OPEN_API_KEY not found in .env")


def fetch_realtime_arrivals(api_key: str, station_name: str) -> dict[str, object]:
    normalized_station_name = normalize_station_name(station_name)
    url = f"http://swopenAPI.seoul.go.kr/api/subway/{api_key}/json/realtimeStationArrival/0/100/{normalized_station_name}"
    with httpx.Client(timeout=10.0) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()


def get_station_arrivals_summary(
    api_key: str,
    station_name: str,
    now: datetime,
    fetcher: Callable[[str, str], dict[str, object]] = fetch_realtime_arrivals,
) -> str:
    payload = fetcher(api_key, station_name)
    rows = extract_arrival_rows(payload)
    return build_summary_for_station(station_name, rows, now)


def _parse_cli_args(argv: list[str]) -> tuple[bool, str] | None:
    args = argv[1:]
    if not args:
        return None

    if args[0] == "--json":
        if len(args) < 2:
            return None
        return True, args[1]

    return False, args[0]


def main() -> int:
    parsed_args = _parse_cli_args(sys.argv)
    if parsed_args is None:
        print('사용법: seoul-metro-realtime [--json] "서울역"')
        return 1

    as_json, raw_name = parsed_args
    package_root = Path(__file__).resolve().parents[2]
    env_files = [Path.cwd() / ".env", package_root / ".env", package_root.parent.parent / ".env"]
    api_key = load_api_key(env_files)
    now = datetime.now()
    if as_json:
        payload = fetch_realtime_arrivals(api_key, raw_name)
        rows = extract_arrival_rows(payload)
        print(json.dumps(build_json_for_station(raw_name, rows, now), ensure_ascii=False, indent=2))
        return 0

    print(get_station_arrivals_summary(api_key, raw_name, now))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

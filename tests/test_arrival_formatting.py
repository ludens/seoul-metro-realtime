from datetime import datetime, timezone
from pathlib import Path
import seoul_metro_realtime.get_arrivals as get_arrivals_module
from seoul_metro_realtime.get_arrivals import (
    LINE_NAME_BY_ID,
    adjust_arrival_seconds,
    build_summary_for_station,
    extract_arrival_rows,
    fetch_realtime_arrivals,
    format_arrivals_summary,
    load_api_key,
    parse_api_arrivals,
)


class DummyResponse:
    def __init__(self, payload: dict[str, object]):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class DummyClient:
    def __init__(self, payload: dict[str, object]):
        self.payload = payload
        self.requested_url: str | None = None

    def __enter__(self) -> "DummyClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, url: str) -> DummyResponse:
        self.requested_url = url
        return DummyResponse(self.payload)


def test_adjust_arrival_seconds_accounts_for_receipt_delay():
    now = datetime(2026, 4, 8, 10, 5, 30, tzinfo=timezone.utc)
    receipt = "2026-04-08 10:03:30"
    assert adjust_arrival_seconds(180, receipt, now) == 60


def test_format_arrivals_summary_groups_by_line_name():
    arrivals = [
        {"line_name": "1호선", "train_line_nm": "인천행 - 남영방면", "seconds": 120, "status": "일반", "is_last_train": False},
        {"line_name": "경의중앙선", "train_line_nm": "문산행 - 효창공원앞방면", "seconds": 240, "status": "급행", "is_last_train": True},
    ]

    output = format_arrivals_summary("서울", arrivals)

    assert "서울 실시간 도착정보" in output
    assert "1호선" in output
    assert "- 남영방면" in output
    assert "인천행: 2분 후 도착" in output
    assert "경의중앙선" in output
    assert "- 효창공원앞방면" in output
    assert "문산행: 4분 후 도착 (급행, 막차)" in output


def test_format_arrivals_summary_groups_by_direction_within_line():
    arrivals = [
        {"line_name": "1호선", "train_line_nm": "광운대행 - 남영방면", "seconds": 0, "status": "일반", "is_last_train": False, "arvl_msg2": "용산 도착", "arvl_cd": "1"},
        {"line_name": "1호선", "train_line_nm": "동두천행 - 남영방면", "seconds": 120, "status": "일반", "is_last_train": False},
        {"line_name": "1호선", "train_line_nm": "인천행 - 노량진방면", "seconds": 180, "status": "일반", "is_last_train": False},
    ]

    output = format_arrivals_summary("용산", arrivals)

    assert "1호선" in output
    assert "- 남영방면" in output
    assert "  - 광운대행: 곧 도착" in output
    assert "  - 동두천행: 2분 후 도착" in output
    assert "- 노량진방면" in output
    assert "  - 인천행: 3분 후 도착" in output


def test_format_arrivals_summary_uses_soon_and_removes_duplicate_status_in_train_name():
    arrivals = [
        {
            "line_name": "경의중앙선",
            "train_line_nm": "용문행 - 홍대입구방면 (급행)",
            "seconds": 0,
            "status": "급행",
            "is_last_train": False,
            "arvl_msg2": "가좌 도착",
            "arvl_cd": "1",
        }
    ]

    output = format_arrivals_summary("가좌", arrivals)

    assert "- 홍대입구방면" in output
    assert "  - 용문행: 곧 도착 (급행)" in output
    assert "용문행 - 홍대입구방면 (급행): 곧 도착 (급행)" not in output


def test_format_arrivals_summary_uses_arvl_msg2_for_running_trains():
    arrivals = [
        {
            "line_name": "경의중앙선",
            "train_line_nm": "용문행 - 홍대입구방면 (급행)",
            "seconds": 0,
            "status": "급행",
            "is_last_train": False,
            "arvl_msg2": "[5]번째 전역 (행신)",
            "arvl_cd": "99",
        }
    ]

    output = format_arrivals_summary("가좌", arrivals)

    assert "- 홍대입구방면" in output
    assert "  - 용문행: [5]번째 전역 (행신) (급행)" in output
    assert "곧 도착" not in output


def test_load_api_key_reads_dotenv(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("SEOUL_OPEN_API_KEY=test-key\n", encoding="utf-8")

    assert load_api_key([env_file]) == "test-key"


def test_load_api_key_prefers_existing_environment_variable(monkeypatch):
    monkeypatch.setenv("SEOUL_OPEN_API_KEY", "env-key")

    assert load_api_key([]) == "env-key"


def test_main_loads_dotenv_from_current_working_directory(tmp_path: Path, monkeypatch, capsys):
    env_file = tmp_path / ".env"
    env_file.write_text("SEOUL_OPEN_API_KEY=cwd-key\n", encoding="utf-8")

    def fake_fetch_realtime_arrivals(api_key: str, station_name: str) -> dict[str, object]:
        assert api_key == "cwd-key"
        assert station_name == "서울역"
        return {"realtimeArrivalList": []}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(get_arrivals_module, "fetch_realtime_arrivals", fake_fetch_realtime_arrivals)
    monkeypatch.setattr(get_arrivals_module, "extract_arrival_rows", lambda payload: [])
    monkeypatch.setattr(get_arrivals_module, "build_summary_for_station", lambda raw_name, rows, now: "ok")
    monkeypatch.setattr(get_arrivals_module.sys, "argv", ["seoul-metro-realtime", "서울역"])

    assert get_arrivals_module.main() == 0
    assert capsys.readouterr().out.strip() == "ok"


def test_extract_arrival_rows_returns_empty_for_info_200():
    payload = {
        "errorMessage": {"status": 200, "code": "INFO-200", "message": "해당하는 데이터가 없습니다."}
    }

    assert extract_arrival_rows(payload) == []


def test_build_summary_for_station_adjusts_and_sorts_arrivals():
    now = datetime(2026, 4, 8, 10, 5, 30, tzinfo=timezone.utc)
    rows = [
        {
            "subwayId": "1001",
            "trainLineNm": "인천행",
            "barvlDt": "180",
            "btrainSttus": "일반",
            "lstcarAt": "0",
            "recptnDt": "2026-04-08 10:03:30",
        },
        {
            "subwayId": "1063",
            "trainLineNm": "문산행",
            "barvlDt": "240",
            "btrainSttus": "급행",
            "lstcarAt": "1",
            "recptnDt": "2026-04-08 10:05:00",
        },
    ]

    output = build_summary_for_station("서울역", rows, now)

    assert output.startswith("서울 실시간 도착정보")
    assert "인천행: 1분 후 도착" in output
    assert "문산행: 3분 후 도착 (급행, 막차)" in output


def test_parse_api_arrivals_maps_subway_id_to_line_name():
    arrivals = parse_api_arrivals([
        {
            "subwayId": "1065",
            "trainLineNm": "인천공항2터미널행 - 홍대입구방면",
            "barvlDt": "0",
            "btrainSttus": "일반",
            "lstcarAt": "0",
            "recptnDt": "2026-04-08 10:03:30",
            "arvlMsg2": "공덕 도착",
            "arvlCd": "1",
        }
    ])

    assert arrivals[0]["line_name"] == "공항철도"


def test_fetch_realtime_arrivals_normalizes_station_name_before_request(monkeypatch):
    payload = {"ok": True}
    dummy_client = DummyClient(payload)

    def fake_client(*args, **kwargs):
        return dummy_client

    monkeypatch.setattr("seoul_metro_realtime.get_arrivals.httpx.Client", fake_client)

    result = fetch_realtime_arrivals("secret-key", "서울역")

    assert result == payload
    assert dummy_client.requested_url is not None
    assert dummy_client.requested_url.endswith("/서울")

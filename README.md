# seoul-metro-realtime

서울 지하철 실시간 도착 정보를 확인하는 Python CLI 도구다.

서울시 Open API의 `realtimeStationArrival` 응답을 읽어 역별 도착 요약을 출력한다.

## 준비

- 서울시 Open API 키
- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) 또는 `pip`

## 사용 방법

### API 키 설정

처음 한 번만 `configure`로 서울시 Open API 키를 저장한다.

```bash
uvx seoul-metro-realtime configure
```

설치해서 쓴다면 아래 명령도 같다.

```bash
seoul-metro-realtime configure
```

설정 파일은 `~/.config/seoul-metro-realtime/config.env`에 저장된다.

환경변수로 직접 넣어도 된다.

```bash
export SEOUL_OPEN_API_KEY=your_api_key_here
```

프로젝트별 키를 쓰려면 현재 작업 디렉터리에 `.env` 파일을 만든다.

`.env`:

```bash
SEOUL_OPEN_API_KEY=your_api_key_here
```

### `uvx`로 바로 실행

`uvx`를 쓰면 설치 없이 바로 실행할 수 있다.

```bash
uvx seoul-metro-realtime 서울역
```

API 키 설정이 없으면 `configure` 실행을 안내한다.

JSON 출력이 필요하면 `--json` 옵션을 붙인다.

```bash
uvx seoul-metro-realtime --json 서울역
```

### 설치 후 실행

```bash
pip install seoul-metro-realtime
```

```bash
seoul-metro-realtime 서울역
```

```bash
seoul-metro-realtime --json 서울역
```

환경변수 우선순위는 아래와 같다.

1. `SEOUL_OPEN_API_KEY` 환경변수
2. 현재 작업 디렉터리의 `.env`
3. `~/.config/seoul-metro-realtime/config.env`
4. 패키지 루트의 `.env`

## 출력 형식

기본 출력은 사람이 읽기 쉬운 텍스트다.

```text
서울 실시간 도착정보

1호선
- 남영방면
  - 인천행: 2분 후 도착

경의중앙선
- 효창공원앞방면
  - 문산행: 4분 후 도착 (급행, 막차)
```

`--json` 옵션을 주면 아래 구조로 출력한다.

```json
{
  "station_name": "서울",
  "generated_at": "2026-04-08T10:05:30+00:00",
  "arrivals": [
    {
      "line_name": "1호선",
      "direction": "남영방면",
      "destination": "인천행",
      "eta": "1분 후 도착",
      "seconds": 60,
      "status": "일반",
      "is_last_train": false,
      "arvl_msg2": "",
      "arvl_cd": "99"
    },
    {
      "line_name": "경의중앙선",
      "direction": "효창공원앞방면",
      "destination": "문산행",
      "eta": "3분 후 도착",
      "seconds": 210,
      "status": "급행",
      "is_last_train": true,
      "arvl_msg2": "",
      "arvl_cd": "99"
    }
  ]
}
```

### JSON 필드 설명

- `station_name`: `역` 접미사를 제거한 역 이름
- `generated_at`: 응답을 가공한 시각 ISO 8601 문자열
- `arrivals`: 도착 예정 정보 배열
- `line_name`: 호선 이름
- `direction`: 방면 정보
- `destination`: 행선지
- `eta`: 사람이 읽기 쉬운 도착 문구
- `seconds`: 보정된 남은 초
- `status`: 열차 상태. 예: `일반`, `급행`
- `is_last_train`: 막차 여부
- `arvl_msg2`: Open API 원본 도착 메시지
- `arvl_cd`: Open API 원본 도착 코드

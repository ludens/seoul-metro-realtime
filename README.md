# seoul-metro-realtime

서울시 지하철 실시간 도착정보를 조회하는 Python CLI 도구다.

서울시 Open API의 `realtimeStationArrival` 응답을 읽어 역별 도착 요약을 사람이 읽기 쉬운 형태로 출력한다.

## 요구 사항

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- 서울시 Open API 키

## 빠른 시작

### 1. API 키 준비

현재 작업 디렉터리에 `.env` 파일을 만들고 키를 넣는다.

```bash
cp .env.example .env
```

`.env`:

```bash
SEOUL_OPEN_API_KEY=your_api_key_here
```

또는 환경변수로 직접 넣어도 된다.

```bash
export SEOUL_OPEN_API_KEY=your_api_key_here
```

### 2. 로컬 프로젝트에서 실행

```bash
uv run seoul-metro-realtime 서울역
```

또는 아직 publish 전이라면 `uvx --from .` 로도 실행할 수 있다.

```bash
uvx --from . seoul-metro-realtime 서울역
```

## `uvx`에서 `.env` 처리

우선순위는 아래와 같다.

1. `SEOUL_OPEN_API_KEY` 환경변수
2. 현재 작업 디렉터리의 `.env`
3. 패키지 루트의 `.env`

즉, publish 후에도 아래처럼 현재 디렉터리에 `.env` 가 있으면 된다.

```bash
uvx seoul-metro-realtime 서울역
```

## 출력 예시

```text
서울 실시간 도착정보

1호선
- 남영방면
  - 인천행: 2분 후 도착

경의중앙선
- 효창공원앞방면
  - 문산행: 4분 후 도착 (급행, 막차)
```

## 개발

의존성 설치 및 테스트:

```bash
uv sync
uv run pytest -v
```

배포 아티팩트 빌드:

```bash
uv build --no-sources
```

## 배포

### GitHub Actions 수동 배포

저장소에는 수동 실행용 GitHub Actions workflow 가 포함되어 있다.

파일:

- `.github/workflows/publish-pypi.yml`

동작:

- `workflow_dispatch` 로 수동 실행
- `uv sync --group dev`
- `uv run pytest -v`
- `uv build --no-sources`
- GitHub Actions secret `PYPI_API_TOKEN` 으로 업로드

사전 준비:

1. PyPI 에서 API token 을 발급한다.
2. GitHub 저장소 Settings > Secrets and variables > Actions 에 `PYPI_API_TOKEN` secret 을 추가한다.
3. GitHub 저장소의 Actions 탭에서 `Publish to PyPI` workflow 를 수동 실행한다.

주의:

- 패키지 이름이 PyPI에서 사용 가능해야 한다
- 같은 버전은 다시 업로드할 수 없다
- PyPI token 은 보통 `pypi-` 로 시작하며, GitHub secret 이름은 정확히 `PYPI_API_TOKEN` 이어야 한다

### 로컬에서 직접 배포

PyPI 인증이 준비되어 있으면 아래도 가능하다.

```bash
uv publish
```

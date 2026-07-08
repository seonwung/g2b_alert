# 나라장터 키워드 알림

나라장터 입찰공고를 주기적으로 조회하고, 설정한 키워드가 공고명/기관명/수요기관명에 포함되면 윈도우 알림을 띄우는 프로그램입니다.

## 배포 방법

exe로 배포할 때는 기본적으로 아래 파일 하나만 전달하면 됩니다.

```text
g2b_alert.exe
```

처음 실행하면 exe가 있는 폴더에 아래 파일과 폴더가 자동으로 생깁니다.

```text
config.json
data/
logs/
```

사용자는 프로그램 화면에서 API 키, 키워드, 조회 주기를 입력하고 시작하면 됩니다. 입력한 값은 `config.json`에 저장됩니다.

## 개발 환경에서 실행

처음 한 번만 필요한 패키지를 설치합니다.

```bat
pip install -r requirements.txt
```

프로그램 실행:

```bat
python main.py
```

## 설정 파일

`config.json`은 없으면 자동으로 만들어집니다.

- `api_key`: 공공데이터포털에서 발급받은 나라장터 API 키입니다.
- `keywords`: 찾을 키워드입니다. 쉼표로 구분해서 적습니다.
- `interval`: 몇 분마다 조회할지 정합니다.
- `selected_categories`: 조회할 공고 종류입니다.
- `bootstrap_minutes`: 처음 실행하거나 기록을 초기화했을 때 최근 몇 분을 조회할지 정합니다.
- `overlap_minutes`: API 반영 지연을 고려해서 이전 조회 시각보다 몇 분 더 겹쳐 조회할지 정합니다.
- `request_timeout_seconds`: API 응답을 기다리는 최대 시간입니다.
- `num_of_rows`: 한 번에 가져올 공고 수입니다.

`selected_categories`에는 아래 영문 코드를 넣습니다.

- `service`: 용역
- `goods`: 물품
- `works`: 공사
- `etc`: 기타

## 폴더 구조

```text
g2b_alert/
  main.py
  config.json
  config.example.json
  requirements.txt
  build_exe.bat
  README.md
  data/
    seen_bids.json
    state.json
  logs/
    g2b_alert.log
  g2b_alert/
    app_logger.py
    config_manager.py
    g2b_client.py
    keyword_matcher.py
    notifier.py
    paths.py
    scheduler.py
    ui.py
```

## 각 파일 역할

- `main.py`: 프로그램 시작점입니다.
- `config.json`: 실제 실행에 사용하는 설정 파일입니다. 없으면 자동으로 만들어집니다.
- `config.example.json`: 설정 예시 파일입니다.
- `requirements.txt`: 설치해야 하는 파이썬 패키지 목록입니다.
- `build_exe.bat`: PyInstaller로 exe 파일을 만드는 배치 파일입니다.
- `data/seen_bids.json`: 이미 알림을 보낸 공고 기록입니다.
- `data/state.json`: 마지막으로 조회한 시간을 저장합니다.
- `logs/g2b_alert.log`: 오류와 실행 기록이 남는 로그 파일입니다.
- `g2b_alert/paths.py`: exe 또는 개발 실행 기준으로 저장 위치를 정합니다.
- `g2b_alert/config_manager.py`: 설정 파일과 상태 파일을 읽고 저장합니다.
- `g2b_alert/g2b_client.py`: 나라장터 API 주소와 요청 로직을 담당합니다.
- `g2b_alert/keyword_matcher.py`: 공고 정보에서 키워드가 포함되어 있는지 검사합니다.
- `g2b_alert/notifier.py`: 윈도우 알림을 보냅니다.
- `g2b_alert/scheduler.py`: 정해진 시간 간격마다 조회를 반복합니다.
- `g2b_alert/app_logger.py`: 오류와 실행 기록을 로그 파일에 남깁니다.
- `g2b_alert/ui.py`: 사용자가 보는 화면과 버튼 동작을 담당합니다.

## 로그 확인

오류가 나거나 알림이 오지 않으면 먼저 아래 파일을 확인하세요.

```text
logs/g2b_alert.log
```

로그 폴더가 없으면 프로그램이 자동으로 만듭니다.

## exe 만들기

아래 파일을 더블클릭하거나 명령 프롬프트에서 실행합니다.

```bat
build_exe.bat
```

완료 후 실행 파일은 아래 위치에 생성됩니다.

```text
dist/g2b_alert.exe
```

## 유지보수 가이드

키워드를 바꾸려면 프로그램 화면에서 수정한 뒤 시작하면 됩니다. 직접 파일을 수정하려면 `config.json`의 `keywords`를 바꾸면 됩니다.

API 키는 프로그램 화면에 입력하거나 `config.json`의 `api_key`에 넣습니다. 코드 파일에는 API 키를 넣지 않습니다.

조회 시간 간격은 프로그램 화면의 확인 주기 입력칸 또는 `config.json`의 `interval`에서 바꿉니다. 너무 짧게 설정하면 API 호출량이 많아질 수 있으므로 5분 이상을 권장합니다.

알림이 안 올 때는 API 키가 맞는지, 키워드가 너무 좁지 않은지, 조회할 공고 종류가 체크되어 있는지, `logs/g2b_alert.log`에 API 오류가 남았는지 확인하세요.

exe로 다시 만들 때는 `build_exe.bat`을 실행합니다. 코드가 바뀐 뒤에는 새로 빌드해야 합니다.
# g2b_alert

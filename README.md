# 나라장터 키워드 알림

나라장터 입찰공고를 주기적으로 조회하고, 설정한 키워드가 공고명/기관명/수요기관명에 포함되면 윈도우 알림을 띄우는 프로그램입니다.

신규 공고와 저장 공고의 낙찰정보를 공통 수신자에게 이메일로 알릴 수 있습니다. Gmail 앱 비밀번호는 설정 파일이나 EXE에 넣지 않고 Windows 자격 증명 관리자에 저장합니다.

## 이메일 알림 설정

1. 공용 발신 전용 Gmail 계정을 만들고 2단계 인증을 켭니다.
2. Google 계정에서 이 프로그램 전용 앱 비밀번호를 생성합니다.
3. 키워드 설정의 `SMTP·수신자 관리`를 엽니다.
4. Gmail 주소와 앱 비밀번호를 입력하고 수신자 이름·이메일을 저장합니다.
5. 신규 공고 수신자는 `키워드 알림`을 체크합니다.
6. 저장 공고의 낙찰정보 수신자는 저장 공고를 선택한 뒤 `이메일 수신자`에서 연결합니다.

SMTP 공개 설정만 `config.json`에 저장됩니다. 앱 비밀번호는 `G2BAlert.SMTP`, 나라장터 API 키는 `G2BAlert.API` 이름으로 Windows 자격 증명 관리자에 보관되며 로그, DB, 설정 파일에는 기록되지 않습니다. Windows 자격 증명 저장 기능을 사용할 수 없는 환경에서는 실행 가능성을 위해 API 키가 설정 파일에 남을 수 있습니다.

메일은 별도 작업자가 발송합니다. 수신자별 성공·실패·재시도 횟수는 DB에 기록되고 `SMTP·수신자 관리` 화면에서 최근 기록을 확인할 수 있습니다. 동일 공고와 낙찰 결과는 고유 이벤트 키로 중복 발송을 막습니다.

## 배포 방법

exe로 배포할 때는 기본적으로 아래 파일 하나만 전달하면 됩니다.

```text
g2b_alert.exe
```

처음 실행하면 사용자별 `%LOCALAPPDATA%\G2BAlert` 폴더에 아래 파일과 폴더가 자동으로 생깁니다.

```text
config.json
data/
  g2b_alert.db
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

`config.json`은 `%LOCALAPPDATA%\G2BAlert`에 없으면 자동으로 만들어집니다.

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
main.py                 실행 진입점
g2b_alert/
  app.py                애플리케이션 진입 클래스
  api/                  외부 통신
    http_client.py       공통 HTTP·안전한 오류 처리
    bid_api.py           입찰공고 API
    result_api.py        개찰·낙찰 API
    smtp_client.py       SMTP 전송
  model/                데이터와 업무 규칙
    entities.py          Bid·SavedBid·BidResult Entity
    bid_model.py         입찰 감시
    result_model.py      저장 공고 결과 감시
    email_model.py       이메일 이벤트 생성 규칙
    config.py            설정
    database.py          DB 연결과 Repository 객체 조립
    repositories/        독립된 입찰·낙찰·이메일 Repository
  presentation/         GUI 툴킷과 무관한 View 계약과 초기 화면 상태
    contracts.py         AppView·ViewActions Protocol과 화면 상태 DTO
  view/                 Tkinter 화면
    main_view.py         메인 화면 골격
    bid_monitor_view.py  감시 설정 화면
    recent_alert_view.py 최근 알림 화면
    saved_bids_view.py   저장 공고 화면
    email_*_view.py      SMTP·수신자 화면
    log_view.py          실행 로그 화면
  controller/           사용자 동작과 Model 연결
    app_controller.py
    bid_monitor_controller.py
    bid_monitor_worker.py
    saved_bids_controller.py
    saved_result_controller.py
    result_monitor_worker.py
    email_controller.py
    email_delivery_worker.py
```

## 각 파일 역할

- `main.py`: Tkinter와 `Application`을 시작하는 최소 실행 진입점입니다.
- `g2b_alert/api`: 나라장터 HTTP API와 SMTP처럼 외부 시스템 통신을 담당합니다.
- `g2b_alert/model`: Entity, 업무 규칙, 설정과 SQLite Repository를 담당하며 UI·스레드·외부 통신을 직접 실행하지 않습니다.
- `g2b_alert/presentation`: Controller와 GUI가 공유하는 툴킷 중립 계약과 초기 화면 상태를 담당합니다.
- `g2b_alert/view`: Tkinter 위젯 생성, 원시 입력 수집과 화면 표시만 담당하며 Controller 설정 객체를 직접 읽지 않습니다.
- `g2b_alert/controller`: 버튼 동작, 입력 정규화, 보수적 주기 Worker 제어, API·Model·View 연결을 담당합니다.
- `config.json`: 실제 실행에 사용하는 설정 파일입니다. 없으면 자동으로 만들어집니다.
- `config.example.json`: 설정 예시 파일입니다.
- `requirements.txt`: 설치해야 하는 파이썬 패키지 목록입니다.
- `build_exe.bat`: PyInstaller로 exe 파일을 만드는 배치 파일입니다.
- `data/g2b_alert.db`: 이미 알림한 공고, 마지막 조회 시각, 저장 공고, 낙찰 결과와 이메일 기록을 저장합니다.
- `logs/g2b_alert.log`: 오류와 실행 기록이 남는 로그 파일입니다.

새 GUI는 `AppViewProtocol`과 `ViewActionsProtocol`을 구현하고 `MainViewState`를 입력받으면 됩니다. 따라서 향후 PySide6 전환에서는 Model과 Controller를 유지한 채 View factory, Qt 이벤트 루프, UI dispatcher와 화면 구현만 교체할 수 있습니다.

## 데이터 계층 선택

이 프로그램은 계층 사이를 네트워크로 연결하는 서버가 아니라 한 프로세스에서 동작하는 데스크톱 앱이므로,
같은 데이터를 계층마다 DTO로 복사하는 `DTO + DAO` 대신 `Entity + Repository`를 사용합니다.

```text
나라장터 JSON → API가 Entity로 변환 → Model의 업무 판단 → Repository → SQLite
SQLite → Repository가 Entity로 복원 → Controller → View
```

- `Bid`, `SavedBid`, `BidResult`는 도메인 데이터를 표현합니다.
- `BidRepository`, `ResultRepository`, `EmailRepository`는 각각 필요한 SQL만 담당합니다.
- `G2BDatabase`는 연결과 테이블 생성 후 세 Repository 객체를 조립합니다.
- Repository는 Mixin 다중 상속을 사용하지 않으며 Model은 필요한 Repository만 전달받습니다.

감시 Worker는 Controller 계층에 있습니다. 한 회차의 API 조회와 저장이 완전히 끝난 다음 설정한 주기만큼 기다리므로 작업이 겹치지 않습니다. 즉, `1분` 설정은 매 시계 분에 정확히 맞추는 방식이 아니라 이전 회차 완료 후 안전하게 1분을 대기하는 보수적인 방식입니다.

## 로그 확인

오류가 나거나 알림이 오지 않으면 먼저 아래 파일을 확인하세요.

```text
%LOCALAPPDATA%\G2BAlert\logs\g2b_alert.log
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

API 키는 프로그램 화면에 입력하며 Windows 자격 증명 관리자에 저장됩니다. 코드 파일에는 API 키를 넣지 않습니다.

조회 시간 간격은 프로그램 화면의 확인 주기 입력칸 또는 `config.json`의 `interval`에서 바꿉니다. 너무 짧게 설정하면 API 호출량이 많아질 수 있으므로 5분 이상을 권장합니다.

알림이 안 올 때는 API 키가 맞는지, 키워드가 너무 좁지 않은지, 조회할 공고 종류가 체크되어 있는지, `%LOCALAPPDATA%\G2BAlert\logs\g2b_alert.log`에 API 오류가 남았는지 확인하세요.

exe로 다시 만들 때는 `build_exe.bat`을 실행합니다. 코드가 바뀐 뒤에는 새로 빌드해야 합니다.
# g2b_alert

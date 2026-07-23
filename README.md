# 나라장터 키워드 알림

나라장터 공고를 키워드 조건으로 감시하고 Windows 알림과 이메일을 전송하는
PySide6 데스크톱 프로그램입니다. 저장 공고의 진행 단계와 개찰·낙찰 결과도
추적할 수 있습니다.

## 요구 환경

- Windows 10/11
- Python 3.11 이상
- 공공데이터포털 일반 인증키

## 설치 및 실행

```powershell
python -m pip install -r requirements.txt
python main.py
```

설정과 데이터는 `%LOCALAPPDATA%\G2BAlert`에 저장됩니다. API 키와 SMTP 앱
비밀번호는 가능한 경우 Windows 자격 증명 관리자를 사용합니다.

## 실행 파일 빌드

```powershell
.\build_exe.bat
```

빌드 결과는 `dist\g2b_alert.exe`입니다. `dist`, 로컬 설정, 데이터베이스와 로그는
Git에 포함되지 않습니다.

## 주요 구성

```text
main.py                    실행 진입점
g2b_alert/api              나라장터·SMTP·Windows 알림 연동
g2b_alert/controller       화면 동작과 업무 흐름 연결
g2b_alert/model            설정, 데이터베이스, 업무 규칙
g2b_alert/presentation     View/Controller 계약
g2b_alert/view             PySide6 화면과 디자인 시스템
g2b_alert/assets           실행에 사용하는 폰트와 아이콘
```

실제 API 키나 SMTP 비밀번호가 포함된 설정 파일은 커밋하지 마세요.

param(
    [string]$OutputPath = (Join-Path (Get-Location) "g2b_alert_code_overview.pptx")
)

$ErrorActionPreference = "Stop"

$ppLayoutBlank = 12
$ppSaveAsOpenXMLPresentation = 24
$msoTextOrientationHorizontal = 1
$msoTrue = -1
$msoFalse = 0

function Add-TextBox {
    param(
        [object]$Slide,
        [string]$Text,
        [double]$Left,
        [double]$Top,
        [double]$Width,
        [double]$Height,
        [int]$FontSize = 20,
        [int]$Color = 0,
        [bool]$Bold = $false
    )

    $shape = $Slide.Shapes.AddTextbox($msoTextOrientationHorizontal, $Left, $Top, $Width, $Height)
    $range = $shape.TextFrame.TextRange
    $range.Text = $Text
    $range.Font.Name = "맑은 고딕"
    $range.Font.Size = $FontSize
    $range.Font.Color.RGB = $Color
    $range.Font.Bold = $(if ($Bold) { $msoTrue } else { $msoFalse })
    $shape.TextFrame.WordWrap = $msoTrue
    return $shape
}

function Add-Bullets {
    param(
        [object]$Slide,
        [string[]]$Items,
        [double]$Left,
        [double]$Top,
        [double]$Width,
        [double]$Height,
        [int]$FontSize = 18
    )

    $text = ($Items | ForEach-Object { "• $_" }) -join "`r"
    $shape = Add-TextBox -Slide $Slide -Text $text -Left $Left -Top $Top -Width $Width -Height $Height -FontSize $FontSize -Color 0x1F2937
    $shape.TextFrame.TextRange.ParagraphFormat.SpaceAfter = 8
    return $shape
}

function Add-Header {
    param(
        [object]$Slide,
        [string]$Title,
        [string]$Subtitle = ""
    )

    $bar = $Slide.Shapes.AddShape(1, 0, 0, 960, 82)
    $bar.Fill.ForeColor.RGB = 0x2563EB
    $bar.Line.Visible = $msoFalse
    Add-TextBox -Slide $Slide -Text $Title -Left 34 -Top 18 -Width 820 -Height 36 -FontSize 25 -Color 0xFFFFFF -Bold $true | Out-Null
    if ($Subtitle) {
        Add-TextBox -Slide $Slide -Text $Subtitle -Left 36 -Top 52 -Width 860 -Height 24 -FontSize 11 -Color 0xDBEAFE | Out-Null
    }
}

function Add-CodeTag {
    param(
        [object]$Slide,
        [string]$Text,
        [double]$Left,
        [double]$Top,
        [double]$Width = 190
    )

    $box = $Slide.Shapes.AddShape(1, $Left, $Top, $Width, 34)
    $box.Fill.ForeColor.RGB = 0xEEF2FF
    $box.Line.ForeColor.RGB = 0xC7D2FE
    $box.TextFrame.TextRange.Text = $Text
    $box.TextFrame.TextRange.Font.Name = "Consolas"
    $box.TextFrame.TextRange.Font.Size = 13
    $box.TextFrame.TextRange.Font.Color.RGB = 0x1D4ED8
    $box.TextFrame.MarginLeft = 10
    $box.TextFrame.MarginRight = 8
    return $box
}

function Add-FlowBox {
    param(
        [object]$Slide,
        [string]$Title,
        [string]$Body,
        [double]$Left,
        [double]$Top,
        [double]$Width,
        [double]$Height,
        [int]$Fill
    )

    $shape = $Slide.Shapes.AddShape(1, $Left, $Top, $Width, $Height)
    $shape.Fill.ForeColor.RGB = $Fill
    $shape.Line.ForeColor.RGB = 0xCBD5E1
    $shape.TextFrame.MarginLeft = 12
    $shape.TextFrame.MarginTop = 9
    $shape.TextFrame.TextRange.Text = "$Title`r$Body"
    $shape.TextFrame.TextRange.Font.Name = "맑은 고딕"
    $shape.TextFrame.TextRange.Font.Size = 14
    $shape.TextFrame.TextRange.Font.Color.RGB = 0x111827
    $shape.TextFrame.TextRange.Characters(1, $Title.Length).Font.Bold = $msoTrue
    $shape.TextFrame.TextRange.Characters(1, $Title.Length).Font.Size = 16
    return $shape
}

function Add-Arrow {
    param(
        [object]$Slide,
        [double]$Left,
        [double]$Top,
        [double]$Width
    )

    $line = $Slide.Shapes.AddLine($Left, $Top, $Left + $Width, $Top)
    $line.Line.ForeColor.RGB = 0x64748B
    $line.Line.Weight = 2
    $line.Line.EndArrowheadStyle = 3
    return $line
}

$slides = @(
    @{
        Title = "g2b_alert 파이썬 코드 기능 정리"
        Subtitle = "나라장터 키워드 알림 프로그램의 모듈별 역할과 실행 흐름"
        Type = "cover"
    },
    @{
        Title = "전체 구조 한눈에 보기"
        Subtitle = "사용자 입력 → 주기적 조회 → 키워드 매칭 → Windows 알림"
        Type = "flow"
    },
    @{
        Title = "진입점: main.py / __init__.py"
        Subtitle = "프로그램을 시작하고 패키지 버전을 표시하는 가장 얇은 층"
        Tags = @("main.py", "g2b_alert/__init__.py")
        Bullets = @(
            "main.py는 Tkinter 루트 창을 만들고 G2BAlertApp을 붙인 뒤 mainloop()를 실행합니다.",
            "if __name__ == '__main__' 패턴으로 직접 실행될 때만 main()이 호출됩니다.",
            "__init__.py는 g2b_alert 폴더를 패키지로 만들고 __version__ = '1.0.0'을 제공합니다.",
            "실제 기능은 대부분 ui.py, scheduler.py, g2b_client.py 같은 하위 모듈에 위임됩니다."
        )
    },
    @{
        Title = "화면 담당: ui.py"
        Subtitle = "Tkinter 화면, 버튼 이벤트, 사용자 입력 검증을 맡는 중심 모듈"
        Tags = @("G2BAlertApp", "start()", "reset_records()")
        Bullets = @(
            "API 키, 확인 주기, 공고 종류, 키워드를 입력받는 GUI를 구성합니다.",
            "시작 버튼을 누르면 화면 값을 AppConfig로 만들고 필수값과 주기를 검증합니다.",
            "검증이 통과하면 설정을 저장하고 BidScheduler를 생성해 백그라운드 감시를 시작합니다.",
            "로그 창에는 시간 prefix를 붙여 메시지를 남기고, URL은 클릭 가능한 링크로 처리합니다.",
            "감시 중에는 입력칸과 카테고리 체크박스를 비활성화해 실행 중 설정 변경을 막습니다."
        )
    },
    @{
        Title = "설정과 경로: config_manager.py / paths.py"
        Subtitle = "config.json, data 폴더, 실행 위치를 일관되게 관리"
        Tags = @("AppConfig", "load_config()", "get_app_dir()")
        Bullets = @(
            "AppConfig dataclass가 API 키, 키워드, 조회 주기, 카테고리, 조회 옵션의 기본값을 정의합니다.",
            "load_json()은 파일이 없거나 깨져도 기본값을 반환해 프로그램 시작 실패를 줄입니다.",
            "save_json()은 부모 폴더를 자동 생성하고 UTF-8 JSON으로 저장합니다.",
            "환경변수 G2B_API_KEY가 있으면 config.json보다 우선 적용됩니다.",
            "paths.py는 일반 실행과 PyInstaller exe 실행을 구분해 앱 기준 폴더를 계산합니다."
        )
    },
    @{
        Title = "나라장터 API 클라이언트: g2b_client.py"
        Subtitle = "카테고리별 엔드포인트 호출과 응답 데이터를 BidItem으로 변환"
        Tags = @("G2BClient", "BidItem", "parse_items()")
        Bullets = @(
            "CATEGORY_LABELS와 ENDPOINTS가 service/goods/works/etc를 실제 API 경로와 한글 이름으로 매핑합니다.",
            "fetch_bids()는 조회 시작/종료 시간을 yyyyMMddHHmm 형식으로 바꿔 requests.get()을 호출합니다.",
            "response.raise_for_status()로 HTTP 오류를 예외로 올려 스케줄러가 실패를 감지하게 합니다.",
            "parse_items()는 API 응답의 items가 None, dict, list 등으로 달라져도 리스트 형태로 맞춥니다.",
            "BidItem.unique_id는 공고번호와 차수를 합쳐 중복 알림을 구분하는 키로 사용됩니다."
        )
    },
    @{
        Title = "키워드 매칭: keyword_matcher.py"
        Subtitle = "공백과 일부 기호를 제거해 조금 더 유연하게 포함 여부를 검사"
        Tags = @("normalize()", "parse_keywords()", "match_keywords()")
        Bullets = @(
            "parse_keywords()는 쉼표와 줄바꿈으로 입력된 키워드를 리스트로 바꿉니다.",
            "normalize()는 소문자 변환, 공백 제거, -_/.,(){}[]:; 같은 기호 제거를 수행합니다.",
            "match_keywords()는 제목, 공고기관, 수요기관을 합친 문자열에서 키워드 포함 여부를 확인합니다.",
            "정규식 re.sub()을 사용해 사람이 입력한 표현 차이를 어느 정도 흡수합니다.",
            "현재 방식은 단순 포함 검색이라 빠르고 이해하기 쉽지만, 형태소 분석이나 AND/OR 조건은 없습니다."
        )
    },
    @{
        Title = "주기 실행 핵심: scheduler.py"
        Subtitle = "백그라운드 스레드에서 API 조회, 중복 제거, 알림 발송을 조율"
        Tags = @("BidScheduler", "check_once()", "_loop()")
        Bullets = @(
            "start()는 daemon Thread를 만들고 _loop()를 백그라운드에서 실행합니다.",
            "_loop()는 check_once() 실행 후 설정된 interval 분만큼 1초 단위로 대기합니다.",
            "check_lock으로 같은 시점에 조회가 겹치지 않도록 막습니다.",
            "state.json의 last_check_time을 기준으로 조회 시작 시각을 정하고 overlap_minutes만큼 겹쳐 조회합니다.",
            "카테고리별로 API를 호출하고 새 공고 중 키워드가 매칭된 경우에만 _send_alert()를 호출합니다.",
            "모든 조회가 성공했을 때만 last_check_time을 갱신해 실패 구간을 놓치지 않게 합니다."
        )
    },
    @{
        Title = "알림과 로그: notifier.py / app_logger.py"
        Subtitle = "사용자에게는 Windows 토스트, 개발자에게는 회전 로그 파일"
        Tags = @("WindowsNotifier", "setup_logger()")
        Bullets = @(
            "notifier.py는 winotify가 설치되어 있으면 Windows 알림을 띄웁니다.",
            "winotify가 없으면 프로그램을 중단하지 않고 logger.warning()만 남깁니다.",
            "알림 메시지는 카테고리, 제목, 기관, 공고번호, 차수, 매칭 키워드를 포함합니다.",
            "app_logger.py는 logs/g2b_alert.log에 RotatingFileHandler를 붙입니다.",
            "로그 파일은 1MB 단위로 최대 5개까지 보관되어 장시간 실행에도 파일이 무한히 커지지 않습니다."
        )
    },
    @{
        Title = "저장되는 데이터 파일"
        Subtitle = "프로그램 상태를 JSON으로 남겨 재실행해도 이어서 감시"
        Tags = @("config.json", "data/seen_bids.json", "data/state.json")
        Bullets = @(
            "config.json: API 키, 키워드, 주기, 선택 카테고리 등 사용자 설정을 저장합니다.",
            "seen_bids.json: 이미 알림을 보낸 공고의 unique_id 목록을 저장해 중복 알림을 막습니다.",
            "state.json: 마지막 조회 성공 시각을 저장해 다음 실행 때 이어서 조회합니다.",
            "확인 기록 초기화 버튼은 seen_bids.json과 state.json을 삭제해 기존 공고도 다시 검사할 수 있게 합니다.",
            "JSON 저장은 config_manager.save_json() 한 곳에서 처리되어 인코딩과 폴더 생성 방식이 통일됩니다."
        )
    },
    @{
        Title = "실행 흐름을 코드로 따라가기"
        Subtitle = "처음 읽을 때는 이 순서로 보면 전체 그림이 빠르게 잡힙니다."
        Tags = @("main → ui → scheduler → client/matcher/notifier")
        Bullets = @(
            "1. main.py: Tkinter 앱이 어떻게 시작되는지 확인합니다.",
            "2. ui.py의 start(): 화면 입력값이 어떻게 설정 객체와 스케줄러로 이어지는지 봅니다.",
            "3. scheduler.py의 check_once(): 실제 감시 로직 대부분이 들어 있는 핵심 함수입니다.",
            "4. g2b_client.py: 외부 API 호출과 응답 변환 방식을 확인합니다.",
            "5. keyword_matcher.py와 notifier.py: 매칭 조건과 알림 출력 방식을 마무리로 보면 됩니다."
        )
    },
    @{
        Title = "파이썬 관점에서 볼 만한 포인트"
        Subtitle = "초중급 단계에서 배우기 좋은 문법과 설계 요소"
        Tags = @("dataclass", "threading", "callback", "JSON", "exception")
        Bullets = @(
            "dataclass: AppConfig와 BidItem처럼 데이터 묶음을 간결하게 표현합니다.",
            "callback 함수: scheduler는 on_log, on_status를 직접 모르고 호출만 하므로 UI와 로직이 느슨하게 연결됩니다.",
            "threading: Tkinter 화면이 멈추지 않도록 API 조회를 별도 스레드에서 실행합니다.",
            "예외 처리: API 실패, JSON 읽기 실패, 알림 모듈 부재를 프로그램 전체 중단으로 만들지 않습니다.",
            "작은 모듈 분리: UI, 설정, API, 매칭, 알림, 로그가 각자 맡은 책임을 갖고 있어 유지보수가 쉽습니다."
        )
    },
    @{
        Title = "개선 아이디어"
        Subtitle = "현재 구조를 유지하면서 다음 단계로 확장할 수 있는 부분"
        Tags = @("테스트", "페이지네이션", "비동기", "검색 조건")
        Bullets = @(
            "API 결과가 numOfRows보다 많을 수 있으므로 pageNo 반복 조회를 추가할 수 있습니다.",
            "keyword_matcher.py에 단위 테스트를 붙이면 키워드 정규화 규칙을 바꿀 때 안정성이 좋아집니다.",
            "설정값 interval이 문자열로 저장되므로 UI 검증 뒤 내부에서는 int로 다루면 타입이 더 명확해집니다.",
            "키워드 조건을 단순 포함에서 AND/OR, 제외 키워드, 대소문자 옵션 등으로 확장할 수 있습니다.",
            "UI와 스케줄러 사이 이벤트 큐를 도입하면 스레드 간 Tkinter 업데이트를 더 체계적으로 관리할 수 있습니다."
        )
    }
)

$powerPoint = $null
$presentation = $null

try {
    $powerPoint = New-Object -ComObject PowerPoint.Application
    $presentation = $powerPoint.Presentations.Add()
    $presentation.PageSetup.SlideWidth = 960
    $presentation.PageSetup.SlideHeight = 540

    foreach ($slideData in $slides) {
        $slide = $presentation.Slides.Add($presentation.Slides.Count + 1, $ppLayoutBlank)
        $slide.Background.Fill.ForeColor.RGB = 0xF8FAFC

        if ($slideData.Type -eq "cover") {
            $banner = $slide.Shapes.AddShape(1, 0, 0, 960, 540)
            $banner.Fill.ForeColor.RGB = 0xEEF2FF
            $banner.Line.Visible = $msoFalse
            $accent = $slide.Shapes.AddShape(1, 0, 0, 960, 92)
            $accent.Fill.ForeColor.RGB = 0x2563EB
            $accent.Line.Visible = $msoFalse
            Add-TextBox -Slide $slide -Text $slideData.Title -Left 70 -Top 178 -Width 820 -Height 68 -FontSize 33 -Color 0x111827 -Bold $true | Out-Null
            Add-TextBox -Slide $slide -Text $slideData.Subtitle -Left 72 -Top 252 -Width 780 -Height 34 -FontSize 18 -Color 0x374151 | Out-Null
            Add-TextBox -Slide $slide -Text "대상: 파이썬 기본 문법과 함수/클래스를 어느 정도 아는 독자" -Left 72 -Top 328 -Width 760 -Height 30 -FontSize 15 -Color 0x1D4ED8 | Out-Null
            Add-TextBox -Slide $slide -Text "파일 기준: main.py + g2b_alert/*.py" -Left 72 -Top 362 -Width 720 -Height 26 -FontSize 13 -Color 0x6B7280 | Out-Null
            continue
        }

        Add-Header -Slide $slide -Title $slideData.Title -Subtitle $slideData.Subtitle

        if ($slideData.Type -eq "flow") {
            Add-FlowBox -Slide $slide -Title "1. 화면 입력" -Body "ui.py`rAPI 키, 키워드, 주기, 카테고리" -Left 52 -Top 150 -Width 155 -Height 92 -Fill 0xDBEAFE | Out-Null
            Add-Arrow -Slide $slide -Left 214 -Top 196 -Width 45 | Out-Null
            Add-FlowBox -Slide $slide -Title "2. 감시 루프" -Body "scheduler.py`rThread + interval + 상태 저장" -Left 266 -Top 150 -Width 165 -Height 92 -Fill 0xDCFCE7 | Out-Null
            Add-Arrow -Slide $slide -Left 438 -Top 196 -Width 45 | Out-Null
            Add-FlowBox -Slide $slide -Title "3. API 조회" -Body "g2b_client.py`r나라장터 공고 JSON 수집" -Left 490 -Top 150 -Width 165 -Height 92 -Fill 0xFEF3C7 | Out-Null
            Add-Arrow -Slide $slide -Left 662 -Top 196 -Width 45 | Out-Null
            Add-FlowBox -Slide $slide -Title "4. 알림" -Body "matcher + notifier`r키워드 매칭 후 토스트 표시" -Left 714 -Top 150 -Width 170 -Height 92 -Fill 0xFCE7F3 | Out-Null

            Add-FlowBox -Slide $slide -Title "보조 모듈" -Body "config_manager.py: 설정/JSON`rpaths.py: 실행 기준 경로`rapp_logger.py: 파일 로그" -Left 76 -Top 318 -Width 350 -Height 105 -Fill 0xF1F5F9 | Out-Null
            Add-FlowBox -Slide $slide -Title "상태 파일" -Body "config.json: 사용자 설정`rseen_bids.json: 알림 완료 목록`rstate.json: 마지막 조회 시각" -Left 536 -Top 318 -Width 350 -Height 105 -Fill 0xF1F5F9 | Out-Null
            continue
        }

        $tagTop = 106
        foreach ($tag in $slideData.Tags) {
            Add-CodeTag -Slide $slide -Text $tag -Left 48 -Top $tagTop -Width 250 | Out-Null
            $tagTop += 42
        }

        Add-Bullets -Slide $slide -Items $slideData.Bullets -Left 338 -Top 112 -Width 560 -Height 350 -FontSize 17 | Out-Null
    }

    $resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
    if (Test-Path $resolvedOutput) {
        Remove-Item -LiteralPath $resolvedOutput -Force
    }
    $presentation.SaveAs($resolvedOutput, $ppSaveAsOpenXMLPresentation)
}
finally {
    if ($presentation -ne $null) {
        $presentation.Close()
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($presentation)
    }
    if ($powerPoint -ne $null) {
        $powerPoint.Quit()
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($powerPoint)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

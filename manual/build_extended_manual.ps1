$ErrorActionPreference = "Stop"

$sourcePdf = "C:\Users\test\Desktop\나라장터_키워드_알림_사용법.pdf"
$scriptDirectory = Join-Path (Get-Location) "manual"
$outputDocx = Join-Path $scriptDirectory "나라장터_키워드_알림_사용법_기능추가.docx"
$outputPdf = Join-Path $scriptDirectory "나라장터_키워드_알림_사용법_기능추가.pdf"

$wdFormatDocumentDefault = 16
$wdExportFormatPDF = 17

$mainColor = 14175773
$subColor = 5325111
$bodyColor = 2562065

$word = $null
$document = $null

function Set-ParagraphText {
    param($Paragraph, [string]$Text)
    $range = $Paragraph.Range.Duplicate
    $range.End = $range.End - 1
    $range.Text = $Text
}

function Add-ManualParagraph {
    param(
        $Document,
        [ref]$Position,
        [string]$Text,
        [ValidateSet("Main", "Sub", "Body", "Note")]
        [string]$Kind = "Body",
        [bool]$PageBreakBefore = $false
    )

    $start = $Position.Value
    $insert = $Document.Range($start, $start)
    $insert.InsertBefore($Text + "`r")

    $range = $Document.Range($start, $start + $Text.Length)
    $range.Font.Name = "맑은 고딕"
    $range.Font.NameFarEast = "맑은 고딕"
    $range.Font.Color = $bodyColor
    $range.ParagraphFormat.SpaceAfter = 6
    $range.ParagraphFormat.LineSpacingRule = 0

    switch ($Kind) {
        "Main" {
            $range.Font.Size = 14.5
            $range.Font.Bold = 1
            $range.Font.Color = $mainColor
            $range.ParagraphFormat.SpaceBefore = 14
            $range.ParagraphFormat.SpaceAfter = 8
            $range.ParagraphFormat.KeepWithNext = -1
            $range.ParagraphFormat.PageBreakBefore = $(if ($PageBreakBefore) { -1 } else { 0 })
        }
        "Sub" {
            $range.Font.Size = 11.5
            $range.Font.Bold = 1
            $range.Font.Color = $subColor
            $range.ParagraphFormat.SpaceBefore = 10
            $range.ParagraphFormat.SpaceAfter = 5
            $range.ParagraphFormat.KeepWithNext = -1
        }
        "Note" {
            $range.Font.Size = 9
            $range.Font.Bold = 0
            $range.Font.Color = 8417899
        }
        default {
            $range.Font.Size = 10.5
            $range.Font.Bold = 0
        }
    }

    $Position.Value = $start + $Text.Length + 1
}

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Open($sourcePdf, $false, $false)

    # 공개 문서에 실제 인증키가 남지 않도록 기존 2장의 키 문구를 안전하게 교체합니다.
    foreach ($paragraph in $document.Paragraphs) {
        $text = ($paragraph.Range.Text -replace "[\r\a]", "").Trim()
        if ($text -eq "2. 이 프로그램에 사용할 기본 API 키") {
            Set-ParagraphText $paragraph "2. 이 프로그램에 사용할 API 키"
        }
        elseif ($text -eq "초기 설정에 사용할 API 키:") {
            Set-ParagraphText $paragraph "공공데이터포털에서 본인 계정으로 발급받은 API 키를 사용합니다."
        }
        elseif ($text -match "^[0-9a-fA-F]{40,}$") {
            Set-ParagraphText $paragraph "API 키는 비밀번호처럼 관리하고 공개 문서나 저장소에 기록하지 마세요."
        }
    }

    $referenceParagraph = $null
    foreach ($paragraph in $document.Paragraphs) {
        $text = ($paragraph.Range.Text -replace "[\r\a]", "").Trim()
        if ($text -eq "7. 참고 정보") {
            $referenceParagraph = $paragraph
            break
        }
    }
    if (-not $referenceParagraph) {
        throw "원본 문서에서 '7. 참고 정보' 절을 찾지 못했습니다."
    }

    $position = $referenceParagraph.Range.Start

    Add-ManualParagraph $document ([ref]$position) "7. 저장 공고 기능" "Main" $true
    Add-ManualParagraph $document ([ref]$position) "7-1. 최근 알림에서 공고 저장" "Sub"
    Add-ManualParagraph $document ([ref]$position) "키워드 감시 화면의 최근 알림 목록에서 필요한 공고를 선택한 뒤 선택한 공고 저장 버튼을 누릅니다."
    Add-ManualParagraph $document ([ref]$position) "저장한 공고는 저장 공고 페이지에 표시되며, 프로그램의 SQLite 데이터베이스에 보관됩니다. 같은 공고를 다시 저장해도 중복으로 추가되지 않습니다."
    Add-ManualParagraph $document ([ref]$position) "7-2. 입찰공고번호로 직접 조회하여 저장" "Sub"
    Add-ManualParagraph $document ([ref]$position) "최근 알림에서 찾지 못한 공고는 저장 공고 페이지 위쪽의 공고번호 직접 조회에서 확인할 수 있습니다."
    Add-ManualParagraph $document ([ref]$position) "입찰공고번호와 필요한 경우 차수를 입력하고 조회를 누릅니다. 조회 결과의 공고명과 기관을 확인한 뒤 조회 공고 저장을 누릅니다."
    Add-ManualParagraph $document ([ref]$position) "공고번호가 정확해도 API에 아직 데이터가 없거나 공고 유형에 따라 조회가 지원되지 않으면 결과가 표시되지 않을 수 있습니다."
    Add-ManualParagraph $document ([ref]$position) "7-3. 저장 목록 관리" "Sub"
    Add-ManualParagraph $document ([ref]$position) "저장 목록에서는 공고명, 공고번호, 기관명으로 검색할 수 있습니다. 공고를 선택하면 상세 정보 확인, 나라장터 링크 열기, 낙찰정보 조회대상 전환, 이메일 수신자 지정 기능을 사용할 수 있습니다."
    Add-ManualParagraph $document ([ref]$position) "삭제를 누르면 선택한 저장 공고와 연결된 낙찰정보가 함께 삭제되므로 필요한 자료인지 확인한 뒤 진행하세요."

    Add-ManualParagraph $document ([ref]$position) "8. 낙찰정보 조회 및 자동 감시" "Main" $true
    Add-ManualParagraph $document ([ref]$position) "8-1. 조회대상 설정" "Sub"
    Add-ManualParagraph $document ([ref]$position) "저장 공고를 선택하고 조회대상 전환을 눌러 낙찰정보 자동 감시 대상에 포함하거나 제외합니다. 목록의 조회대상 상태가 ON인 공고만 설정한 주기에 따라 확인됩니다."
    Add-ManualParagraph $document ([ref]$position) "낙찰정보 감시 주기에 원하는 분 단위를 입력하고 주기 적용을 누릅니다. 지나치게 짧은 주기는 API 호출량을 늘릴 수 있으므로 필요한 범위에서 설정하세요."
    Add-ManualParagraph $document ([ref]$position) "8-2. 즉시 조회와 자동 확인" "Sub"
    Add-ManualParagraph $document ([ref]$position) "낙찰정보 즉시 조회를 누르면 다음 자동 확인 시각을 기다리지 않고 조회대상 공고를 바로 확인합니다. 화면에는 대상 건수, 결과 없음, 실패, 새 결과 건수가 표시됩니다."
    Add-ManualParagraph $document ([ref]$position) "아직 개찰 또는 낙찰 결과가 나라장터에 등록되지 않은 공고는 결과 없음으로 표시됩니다. 오류가 아니라 등록 전 상태일 수 있으므로 이후 주기에 다시 확인하면 됩니다."
    Add-ManualParagraph $document ([ref]$position) "8-3. 새 낙찰정보 알림" "Sub"
    Add-ManualParagraph $document ([ref]$position) "새 낙찰정보가 확인되면 낙찰업체, 금액, 상태 등의 결과가 저장됩니다. 새 낙찰정보 발견 시 윈도우/미확인 알림을 체크하면 Windows 알림과 화면의 미확인 표시로 알려줍니다."
    Add-ManualParagraph $document ([ref]$position) "공고별 상세 화면에서 최근 낙찰정보 조회 시각과 이메일 수신자 수를 함께 확인할 수 있습니다."

    Add-ManualParagraph $document ([ref]$position) "9. 이메일 알림 설정" "Main" $true
    Add-ManualParagraph $document ([ref]$position) "9-1. SMTP와 수신자 등록" "Sub"
    Add-ManualParagraph $document ([ref]$position) "키워드 설정 화면에서 SMTP·수신자 관리를 열고 Gmail 주소, 발신자 이름, 앱 비밀번호를 입력합니다. 일반 Gmail 로그인 비밀번호가 아니라 2단계 인증에서 발급한 앱 비밀번호를 사용합니다."
    Add-ManualParagraph $document ([ref]$position) "앱 비밀번호는 config.json이나 실행 파일에 저장되지 않고 Windows 자격 증명 관리자에 보관됩니다. 수신자 이름과 이메일 주소를 입력한 뒤 저장을 누릅니다."
    Add-ManualParagraph $document ([ref]$position) "9-2. 알림 종류별 수신자 연결" "Sub"
    Add-ManualParagraph $document ([ref]$position) "새 키워드 공고를 받을 사람은 수신자 목록에서 키워드 알림을 체크합니다. 저장 공고의 낙찰정보를 받을 사람은 저장 공고를 선택한 뒤 이메일 수신자에서 개별적으로 연결합니다."
    Add-ManualParagraph $document ([ref]$position) "한 수신자는 키워드 알림과 여러 저장 공고의 낙찰정보 알림을 함께 받을 수 있습니다. 동일한 설정을 반복 입력할 필요는 없습니다."
    Add-ManualParagraph $document ([ref]$position) "9-3. 발송 확인과 문제 해결" "Sub"
    Add-ManualParagraph $document ([ref]$position) "최근 이메일 발송 기록에서 신규 공고와 낙찰정보 메일의 대기, 발송 중, 성공, 실패 상태를 확인할 수 있습니다."
    Add-ManualParagraph $document ([ref]$position) "메일이 발송되지 않으면 인터넷 연결, Gmail 주소, 앱 비밀번호, 수신자 이메일 주소를 확인하세요. 앱 비밀번호를 변경했다면 SMTP·수신자 관리에서 새 비밀번호를 다시 저장해야 합니다."

    Set-ParagraphText $referenceParagraph "10. 참고 정보"
    $referenceParagraph.Range.ParagraphFormat.PageBreakBefore = -1

    $document.SaveAs2($outputDocx, $wdFormatDocumentDefault)
    $document.ExportAsFixedFormat($outputPdf, $wdExportFormatPDF)
}
finally {
    if ($document) { $document.Close($false) }
    if ($word) { $word.Quit() }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

Write-Output $outputPdf

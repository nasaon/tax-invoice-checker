"""세금계산서 발행 도우미 — 한글 PDF 사용 설명서 생성기"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── 한글 폰트 등록 ──────────────────────────────────────────────
FONT_DIR = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Malgun", str(FONT_DIR / "malgun.ttf")))
pdfmetrics.registerFont(TTFont("MalgunBd", str(FONT_DIR / "malgunbd.ttf")))
pdfmetrics.registerFontFamily("Malgun", normal="Malgun", bold="MalgunBd")

# ── 색상 팔레트 ──────────────────────────────────────────────────
BLUE       = colors.HexColor("#2563EB")
LIGHT_BLUE = colors.HexColor("#EFF6FF")
GREEN      = colors.HexColor("#16A34A")
LIGHT_GREEN= colors.HexColor("#F0FDF4")
ORANGE     = colors.HexColor("#EA580C")
LIGHT_ORANGE=colors.HexColor("#FFF7ED")
RED        = colors.HexColor("#DC2626")
LIGHT_RED  = colors.HexColor("#FEF2F2")
GRAY       = colors.HexColor("#6B7280")
LIGHT_GRAY = colors.HexColor("#F9FAFB")
DARK       = colors.HexColor("#111827")
WHITE      = colors.white

W, H = A4  # 595 x 842 pt

# ── 스타일 정의 ──────────────────────────────────────────────────
def make_styles() -> dict:
    return {
        "title": ParagraphStyle("title", fontName="MalgunBd", fontSize=26,
                                 leading=34, textColor=WHITE, alignment=TA_CENTER),
        "subtitle": ParagraphStyle("subtitle", fontName="Malgun", fontSize=13,
                                    leading=20, textColor=colors.HexColor("#BFDBFE"),
                                    alignment=TA_CENTER),
        "h1": ParagraphStyle("h1", fontName="MalgunBd", fontSize=16,
                              leading=24, textColor=BLUE, spaceAfter=4),
        "h2": ParagraphStyle("h2", fontName="MalgunBd", fontSize=13,
                              leading=20, textColor=DARK, spaceBefore=8, spaceAfter=2),
        "body": ParagraphStyle("body", fontName="Malgun", fontSize=11,
                                leading=18, textColor=DARK, spaceAfter=4,
                                alignment=TA_JUSTIFY),
        "body_sm": ParagraphStyle("body_sm", fontName="Malgun", fontSize=10,
                                   leading=16, textColor=DARK),
        "step": ParagraphStyle("step", fontName="MalgunBd", fontSize=11,
                                leading=18, textColor=BLUE, leftIndent=6),
        "bullet": ParagraphStyle("bullet", fontName="Malgun", fontSize=11,
                                  leading=18, textColor=DARK, leftIndent=14,
                                  bulletIndent=4),
        "note": ParagraphStyle("note", fontName="Malgun", fontSize=10,
                                leading=16, textColor=colors.HexColor("#374151")),
        "caption": ParagraphStyle("caption", fontName="Malgun", fontSize=9,
                                   leading=14, textColor=GRAY, alignment=TA_CENTER),
        "tbl_hd": ParagraphStyle("tbl_hd", fontName="MalgunBd", fontSize=10,
                                  leading=14, textColor=WHITE, alignment=TA_CENTER),
        "tbl_bd": ParagraphStyle("tbl_bd", fontName="Malgun", fontSize=10,
                                  leading=15, textColor=DARK),
        "tbl_bd_c": ParagraphStyle("tbl_bd_c", fontName="Malgun", fontSize=10,
                                    leading=15, textColor=DARK, alignment=TA_CENTER),
        "footer": ParagraphStyle("footer", fontName="Malgun", fontSize=8,
                                  leading=12, textColor=GRAY, alignment=TA_CENTER),
    }

S = make_styles()

# ── 헬퍼 ────────────────────────────────────────────────────────
def sp(h: float = 4) -> Spacer:
    return Spacer(1, h * mm)

def hr(color=BLUE, thickness=1) -> HRFlowable:
    return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=4)

def section_header(num: str, title: str) -> list:
    """번호 + 제목 조합 섹션 헤더"""
    tbl = Table(
        [[Paragraph(num, ParagraphStyle("n", fontName="MalgunBd", fontSize=13,
                                         textColor=WHITE, alignment=TA_CENTER)),
          Paragraph(title, S["h1"])]],
        colWidths=[9*mm, W - 40*mm],
        rowHeights=[10*mm],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), BLUE),
        ("BACKGROUND", (1, 0), (1, 0), LIGHT_BLUE),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",(1, 0), (1, 0), 8),
        ("ROUNDEDCORNERS", [3]),
    ]))
    return [sp(4), tbl, sp(3)]

def callout(text: str, bg=LIGHT_BLUE, border=BLUE) -> Table:
    p = Paragraph(text, S["note"])
    tbl = Table([[p]], colWidths=[W - 40*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), bg),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",(0, 0), (-1, -1), 8),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LINEBEFORE",  (0, 0), (0, -1), 3, border),
        ("ROUNDEDCORNERS", [3]),
    ]))
    return tbl

def steps_table(steps: list[tuple[str, str]]) -> Table:
    rows = []
    for num, text in steps:
        rows.append([
            Paragraph(num, ParagraphStyle("sn", fontName="MalgunBd", fontSize=11,
                                           textColor=WHITE, alignment=TA_CENTER)),
            Paragraph(text, S["body_sm"]),
        ])
    tbl = Table(rows, colWidths=[8*mm, W - 50*mm], rowHeights=None)
    style = [
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (1, 0), (1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [LIGHT_BLUE, WHITE]),
    ]
    for i in range(len(steps)):
        style.append(("BACKGROUND", (0, i), (0, i), BLUE))
    tbl.setStyle(TableStyle(style))
    return tbl

def status_badge(text: str, bg: object, fg=WHITE) -> Paragraph:
    style = ParagraphStyle("badge", fontName="MalgunBd", fontSize=9,
                            textColor=fg, alignment=TA_CENTER,
                            backColor=bg, borderPadding=3)
    return Paragraph(text, style)


# ── 표지 ────────────────────────────────────────────────────────
def cover_page() -> list:
    story = []

    # 배경 헤더 블록 (Table 로 배경색 구현)
    header_tbl = Table(
        [[Paragraph("세금계산서 발행 도우미", S["title"])],
         [Paragraph("사용 설명서", S["title"])],
         [sp(2)],
         [Paragraph("누구나 쉽게 따라 할 수 있는 안내서", S["subtitle"])]],
        colWidths=[W - 40*mm],
    )
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), BLUE),
        ("TOPPADDING",   (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(sp(10))
    story.append(header_tbl)
    story.append(sp(8))

    # 요약 카드
    info = [
        ["대상",    "세금계산서를 직접 관리하는 1인 사업자·프리랜서"],
        ["필요 앱", "Jupyter Notebook (또는 JupyterLab)"],
        ["운영체제","Windows 10/11"],
        ["언어",    "Python 3.10 이상"],
    ]
    rows = [[Paragraph(k, ParagraphStyle("ik", fontName="MalgunBd", fontSize=10,
                                          textColor=BLUE)),
             Paragraph(v, S["body_sm"])] for k, v in info]
    card = Table(rows, colWidths=[24*mm, W - 66*mm])
    card.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), LIGHT_BLUE),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
        ("TOPPADDING",   (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(card)
    story.append(sp(6))

    story.append(hr())
    story.append(Paragraph(
        "이 설명서는 세금계산서 발행 도우미 프로그램을 처음 사용하는 분들을 위해 만들어졌습니다. "
        "어려운 단어 없이, 그림처럼 쉽게 따라 할 수 있도록 안내합니다.",
        S["body"]))
    story.append(PageBreak())
    return story


# ── 목차 ────────────────────────────────────────────────────────
def toc_page() -> list:
    story = [Paragraph("목  차", S["h1"]), hr(), sp(4)]
    toc = [
        ("1", "이 프로그램은 무엇인가요?",    "3"),
        ("2", "처음 시작하기 (준비 단계)",     "4"),
        ("3", "노트북 실행하기",               "5"),
        ("4", "샘플 데이터로 연습하기",        "6"),
        ("5", "내 데이터 입력하기",            "7"),
        ("6", "검증 결과 이해하기",            "8"),
        ("7", "발행 큐(Queue) 확인하기",       "9"),
        ("8", "오류 메시지 해결법",            "10"),
        ("9", "자주 묻는 질문 (Q&A)",          "11"),
    ]
    rows = [[Paragraph(n, S["step"]),
             Paragraph(t, S["body_sm"]),
             Paragraph(p, ParagraphStyle("pg", fontName="Malgun", fontSize=10,
                                          textColor=GRAY, alignment=TA_CENTER))]
            for n, t, p in toc]
    tbl = Table(rows, colWidths=[10*mm, W - 65*mm, 15*mm])
    tbl.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [LIGHT_GRAY, WHITE]),
        ("TOPPADDING",   (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
    ]))
    story.append(tbl)
    story.append(PageBreak())
    return story


# ── 본문 섹션들 ──────────────────────────────────────────────────
def section1() -> list:
    story = []
    story += section_header("1", "이 프로그램은 무엇인가요?")

    story.append(Paragraph(
        "이 프로그램은 엑셀 파일에 거래 내용을 입력하면, 세금계산서를 자동으로 "
        "검토하고 발행 준비를 도와주는 도구입니다. 홈택스에 직접 들어갈 필요 없이 "
        "컴퓨터에서 바로 사용할 수 있습니다.", S["body"]))
    story.append(sp(3))

    feat = [
        ["기능",           "설명"],
        ["엑셀 업로드",    "거래 내용이 담긴 엑셀 파일을 불러옵니다"],
        ["자동 검증",      "금액·사업자번호 등 오류를 자동으로 찾아줍니다"],
        ["사업자번호 확인","국세청 API로 거래처 번호가 실제 등록된 것인지 확인합니다"],
        ["발행 큐 생성",   "문제없는 건만 골라 발행 목록을 만들어 줍니다"],
        ["로컬 저장",      "모든 데이터는 내 컴퓨터에만 저장됩니다 (외부 전송 없음)"],
    ]
    tbl = Table(
        [[Paragraph(r[0], S["tbl_hd"] if i == 0 else S["tbl_bd"]),
          Paragraph(r[1], S["tbl_hd"] if i == 0 else S["tbl_bd"])]
         for i, r in enumerate(feat)],
        colWidths=[32*mm, W - 74*mm],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), BLUE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BLUE, WHITE]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
        ("TOPPADDING",   (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(tbl)
    story.append(sp(4))
    story.append(callout(
        "이 프로그램은 인터넷이 없어도 대부분 사용할 수 있습니다.\n"
        "단, 사업자번호 실시간 확인 기능은 인터넷이 필요합니다.",
        LIGHT_GREEN, GREEN))
    story.append(PageBreak())
    return story


def section2() -> list:
    story = []
    story += section_header("2", "처음 시작하기 (준비 단계)")

    story.append(Paragraph("필요한 것들", S["h2"]))
    needs = [
        ["항목",            "확인 방법"],
        ["Python 3.10 이상","명령 프롬프트에서  python --version  입력"],
        ["Jupyter Notebook", "명령 프롬프트에서  jupyter notebook  입력"],
        ["pandas, openpyxl", "pip install pandas openpyxl  로 설치"],
        ["ipywidgets",       "pip install ipywidgets  로 설치"],
        ["공공데이터포털 API 키", "data.go.kr 에서 발급 (선택사항)"],
    ]
    tbl = Table(
        [[Paragraph(r[0], S["tbl_hd"] if i == 0 else S["tbl_bd"]),
          Paragraph(r[1], S["tbl_hd"] if i == 0 else S["tbl_bd_c"] if i == 0 else S["tbl_bd"])]
         for i, r in enumerate(needs)],
        colWidths=[38*mm, W - 80*mm],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), BLUE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BLUE, WHITE]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
        ("TOPPADDING",   (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(tbl)
    story.append(sp(4))

    story.append(Paragraph("API 키 설정 방법 (선택)", S["h2"]))
    story.append(steps_table([
        ("1", "프로그램 폴더에서  .env.example  파일을 찾습니다."),
        ("2", ".env.example  파일을 복사해서 이름을  .env  로 바꿉니다."),
        ("3", ".env  파일을 메모장으로 열고, NTS_API_KEY= 뒤에 발급받은 키를 붙여넣습니다."),
        ("4", "파일을 저장하고 메모장을 닫습니다."),
    ]))
    story.append(sp(3))
    story.append(callout(
        "API 키를 설정하지 않아도 기본 형식 검사는 작동합니다.\n"
        "실제 사업자 등록 여부 확인이 필요할 때만 키가 필요합니다.",
        LIGHT_ORANGE, ORANGE))
    story.append(PageBreak())
    return story


def section3() -> list:
    story = []
    story += section_header("3", "노트북 실행하기")

    story.append(steps_table([
        ("1", "Windows 검색창에  cmd  를 입력하고 명령 프롬프트를 엽니다."),
        ("2", "cd D:\\JJH\\Claude\\co-work  를 입력하고 Enter 를 누릅니다.\n"
              "(프로그램 폴더 위치가 다르면 그 경로로 바꾸세요)"),
        ("3", "jupyter notebook  을 입력하고 Enter 를 누릅니다."),
        ("4", "웹 브라우저가 자동으로 열리면  tax_invoice_internal_app.ipynb  파일을 클릭합니다."),
        ("5", "상단 메뉴에서  Cell  ->  Run All  을 클릭합니다."),
        ("6", "화면 아래쪽에 세금계산서 도우미 화면이 나타납니다!"),
    ]))
    story.append(sp(4))
    story.append(callout(
        "처음 실행하면 아무 데이터도 없어서 비어 보입니다. 정상입니다!\n"
        "4번 섹션을 따라 샘플 데이터를 불러오면 화면이 채워집니다.",
        LIGHT_BLUE, BLUE))
    story.append(PageBreak())
    return story


def section4() -> list:
    story = []
    story += section_header("4", "샘플 데이터로 연습하기")

    story.append(Paragraph(
        "실제 데이터를 입력하기 전에 먼저 샘플 데이터로 연습해 보세요. "
        "샘플 데이터는 가짜 정보로 만들어져 있어 안전합니다.", S["body"]))
    story.append(sp(3))

    story.append(steps_table([
        ("1", "노트북 화면에서  '50건 샘플 데이터 불러오기'  버튼을 클릭합니다."),
        ("2", "잠시 기다리면 아래에 요약 정보가 나타납니다."),
        ("3", "각 색상 카드의 숫자를 확인합니다.\n"
              "  - 파란색: 발행 준비 완료  |  노란색: 거래처 정보 필요\n"
              "  - 빨간색: 오류 발생  |  초록색: 이미 발행됨"),
        ("4", "'발행 큐 미리보기'  버튼을 눌러 어떤 건이 준비됐는지 확인합니다."),
        ("5", "행 번호를 클릭하면 상세 검증 결과를 볼 수 있습니다."),
    ]))
    story.append(sp(4))

    # 상태 카드 설명
    story.append(Paragraph("요약 카드 색상 안내", S["h2"]))
    badge_data = [
        ["색상", "상태",    "뜻"],
        ["파란색",  "발행 대기",    "문제없이 발행할 수 있는 건"],
        ["노란색",  "거래처 보완",  "거래처 사업자번호를 입력해야 하는 건"],
        ["빨간색",  "검증 실패",    "금액 오류 등 수정이 필요한 건"],
        ["초록색",  "발행 완료",    "이미 발행된 건 (중복 발행 방지)"],
    ]
    rows = []
    for i, r in enumerate(badge_data):
        if i == 0:
            rows.append([Paragraph(c, S["tbl_hd"]) for c in r])
        else:
            color_map = {
                "파란색": BLUE, "노란색": colors.HexColor("#D97706"),
                "빨간색": RED,  "초록색": GREEN,
            }
            rows.append([
                Paragraph(r[0], ParagraphStyle("bc", fontName="MalgunBd", fontSize=10,
                                                textColor=WHITE, alignment=TA_CENTER,
                                                backColor=color_map[r[0]])),
                Paragraph(r[1], S["tbl_bd"]),
                Paragraph(r[2], S["tbl_bd"]),
            ])
    tbl = Table(rows, colWidths=[20*mm, 30*mm, W - 92*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), BLUE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_GRAY, WHITE]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(tbl)
    story.append(PageBreak())
    return story


def section5() -> list:
    story = []
    story += section_header("5", "내 데이터 입력하기")

    story.append(Paragraph("엑셀 파일 양식 준비", S["h2"]))
    story.append(Paragraph(
        "엑셀 파일은 정해진 열(컬럼) 순서가 있어야 합니다. "
        "아래 표의 열 이름을 그대로 사용하세요.", S["body"]))
    story.append(sp(2))

    cols = [
        ["열 이름",          "내용",             "예시",             "필수"],
        ["템플릿버전",        "양식 버전",        "2026-05-v1",       "O"],
        ["거래구분",          "매출 또는 매입",    "매출",             "O"],
        ["작성일",            "거래 날짜",        "2026-05-01",       "O"],
        ["거래처명",          "상대방 회사 이름",  "홍길동 디자인",    "O"],
        ["거래처사업자번호",  "10자리 번호",       "123-45-67890",     "O"],
        ["품목",              "판매·구매한 것",    "디자인 용역",      "O"],
        ["공급가액",          "부가세 제외 금액",  "300000",           "O"],
        ["세액",              "공급가액의 10%",    "30000",            "O"],
        ["과세유형",          "현재 과세만 지원",  "과세",             "X"],
        ["발행상태",          "비워 두세요",       "(빈칸)",           "X"],
    ]
    rows = []
    for i, r in enumerate(cols):
        if i == 0:
            rows.append([Paragraph(c, S["tbl_hd"]) for c in r])
        else:
            rows.append([
                Paragraph(r[0], ParagraphStyle("cn", fontName="MalgunBd", fontSize=9,
                                                textColor=BLUE)),
                Paragraph(r[1], S["body_sm"]),
                Paragraph(r[2], ParagraphStyle("ex", fontName="Malgun", fontSize=9,
                                                textColor=GRAY)),
                Paragraph(r[3], ParagraphStyle("req", fontName="MalgunBd", fontSize=10,
                                                textColor=GREEN if r[3]=="O" else GRAY,
                                                alignment=TA_CENTER)),
            ])
    tbl = Table(rows, colWidths=[32*mm, 28*mm, 28*mm, 12*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), BLUE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_BLUE, WHITE]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(tbl)
    story.append(sp(3))
    story.append(callout(
        "팁: 세액 = 공급가액 x 10%  로 계산하면 됩니다.\n"
        "예) 공급가액이 300,000원이면 세액은 30,000원입니다.",
        LIGHT_GREEN, GREEN))
    story.append(sp(3))

    story.append(Paragraph("파일 업로드 방법", S["h2"]))
    story.append(steps_table([
        ("1", "노트북 화면에서  'Excel 파일 선택'  버튼을 클릭합니다."),
        ("2", "내 컴퓨터에서 만든 엑셀 파일을 선택합니다."),
        ("3", "'검증 실행'  버튼을 클릭합니다."),
        ("4", "결과가 나타납니다."),
    ]))
    story.append(PageBreak())
    return story


def section6() -> list:
    story = []
    story += section_header("6", "검증 결과 이해하기")

    story.append(Paragraph(
        "파일을 업로드하고 검증을 실행하면 각 행마다 상태 코드가 붙습니다. "
        "상태 코드의 의미를 알아두면 문제를 빠르게 해결할 수 있습니다.", S["body"]))
    story.append(sp(3))

    statuses = [
        ["상태 코드",     "한국어",      "의미",                          "할 일"],
        ["ready-to-send","발행 대기",    "모든 검사 통과. 발행 가능!",    "큐에 넣으면 됩니다"],
        ["needs-party",  "거래처 보완",  "거래처 사업자번호가 비어 있음", "사업자번호를 입력하세요"],
        ["failed",       "검증 실패",    "금액 오류 또는 형식 오류",      "이슈 내용 확인 후 수정"],
        ["sent",         "발행 완료",    "이미 발행된 건",                "중복 발행 안 됨 (정상)"],
    ]
    colors_map = [None, BLUE, ORANGE, RED, GREEN]
    rows = []
    for i, r in enumerate(statuses):
        if i == 0:
            rows.append([Paragraph(c, S["tbl_hd"]) for c in r])
        else:
            rows.append([
                Paragraph(r[0], ParagraphStyle("sc", fontName="MalgunBd", fontSize=9,
                                                textColor=WHITE, alignment=TA_CENTER,
                                                backColor=colors_map[i])),
                Paragraph(r[1], ParagraphStyle("sk", fontName="MalgunBd", fontSize=10,
                                                textColor=colors_map[i])),
                Paragraph(r[2], S["body_sm"]),
                Paragraph(r[3], S["body_sm"]),
            ])
    tbl = Table(rows, colWidths=[32*mm, 22*mm, 42*mm, W - 146*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), BLUE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_GRAY, WHITE]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(tbl)
    story.append(sp(4))

    story.append(Paragraph("행 상세 보기", S["h2"]))
    story.append(Paragraph(
        "목록에서 행 번호를 클릭하면 오른쪽에 상세 정보가 나타납니다. "
        "'이슈' 항목에 어떤 문제가 있는지 한국어로 설명이 나옵니다.", S["body"]))
    story.append(PageBreak())
    return story


def section7() -> list:
    story = []
    story += section_header("7", "발행 큐(Queue) 확인하기")

    story.append(Paragraph(
        "발행 큐는 '발행 대기' 상태인 건들을 모아둔 대기 목록입니다. "
        "실제로 발행하기 전에 미리 보기로 확인할 수 있습니다.", S["body"]))
    story.append(sp(3))

    queue_statuses = [
        ["큐 상태",          "의미"],
        ["queued",           "발행 준비 완료. 큐에 정상적으로 들어간 건"],
        ["already-sent",     "이미 발행된 건. 자동으로 건너뜁니다"],
        ["blocked",          "검증 실패 또는 거래처 미완성 건. 발행 불가"],
        ["duplicate-blocked","같은 내용이 두 번 이상 입력됨. 중복 차단"],
    ]
    rows = []
    q_colors = [None, BLUE, GREEN, ORANGE, RED]
    for i, r in enumerate(queue_statuses):
        if i == 0:
            rows.append([Paragraph(c, S["tbl_hd"]) for c in r])
        else:
            rows.append([
                Paragraph(r[0], ParagraphStyle("qc", fontName="MalgunBd", fontSize=9,
                                                textColor=WHITE, alignment=TA_CENTER,
                                                backColor=q_colors[i])),
                Paragraph(r[1], S["body_sm"]),
            ])
    tbl = Table(rows, colWidths=[38*mm, W - 80*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), BLUE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_GRAY, WHITE]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(tbl)
    story.append(sp(4))
    story.append(callout(
        "이 프로그램의 현재 버전은 발행 큐 '미리보기'만 지원합니다.\n"
        "실제 발행은 추후 업데이트에서 지원될 예정입니다.",
        LIGHT_ORANGE, ORANGE))
    story.append(PageBreak())
    return story


def section8() -> list:
    story = []
    story += section_header("8", "오류 메시지 해결법")

    errors = [
        ["오류 메시지",                           "원인",                    "해결 방법"],
        ["템플릿버전이 일치하지 않습니다",         "템플릿 버전 오류",        "템플릿버전 열을 2026-05-v1 로 수정"],
        ["거래처 사업자번호가 비어 있습니다",       "사업자번호 없음",         "거래처사업자번호 열에 번호 입력"],
        ["사업자번호 형식이 올바르지 않습니다",     "형식 오류",               "XXX-XX-XXXXX 형식으로 입력"],
        ["세액이 공급가액의 10%와 일치하지 않음",  "금액 계산 오류",          "세액 = 공급가액 x 0.1 로 수정"],
        ["과세 거래만 지원합니다",                 "면세·영세율 미지원",      "현재 버전은 과세 거래만 가능"],
        ["NTS_API_KEY가 설정되지 않았습니다",      "API 키 없음",             ".env 파일에 키 입력 (.env.example 참고)"],
    ]
    rows = []
    for i, r in enumerate(errors):
        if i == 0:
            rows.append([Paragraph(c, S["tbl_hd"]) for c in r])
        else:
            rows.append([
                Paragraph(r[0], ParagraphStyle("em", fontName="Malgun", fontSize=9,
                                                textColor=RED)),
                Paragraph(r[1], S["body_sm"]),
                Paragraph(r[2], ParagraphStyle("fix", fontName="MalgunBd", fontSize=9,
                                                textColor=GREEN)),
            ])
    tbl = Table(rows, colWidths=[55*mm, 30*mm, W - 127*mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), BLUE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [LIGHT_RED, WHITE]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#FECACA")),
        ("TOPPADDING",   (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(tbl)
    story.append(PageBreak())
    return story


def section9() -> list:
    story = []
    story += section_header("9", "자주 묻는 질문 (Q&A)")

    qas = [
        ("Q. 인터넷이 없어도 쓸 수 있나요?",
         "A. 네! 사업자번호 실시간 확인 기능을 빼면 인터넷 없이도 사용 가능합니다."),
        ("Q. 데이터가 어디에 저장되나요?",
         "A. 모든 데이터는 내 컴퓨터의  local_tax_invoice_data  폴더에만 저장됩니다. "
         "외부 서버로 전송되지 않습니다."),
        ("Q. 매입 세금계산서도 관리할 수 있나요?",
         "A. 네! 거래구분 열에  '매입'  을 입력하면 매입 건도 관리할 수 있습니다."),
        ("Q. 파일을 실수로 잘못 올렸어요. 어떻게 하나요?",
         "A. 노트북을 다시 실행(Cell > Run All)하면 초기화됩니다. "
         "잘못 올린 파일의 데이터는 자동으로 지워집니다."),
        ("Q. 같은 건이 두 번 입력되면 어떻게 되나요?",
         "A. 중복 발행 방지 기능이 있어서 같은 내용이 두 번 입력되면 "
         "'duplicate-blocked' 상태로 자동 차단됩니다."),
        ("Q. API 키를 잃어버렸어요.",
         "A. data.go.kr 마이페이지에서 키를 재발급받으세요. "
         "그 다음 .env 파일의 NTS_API_KEY 값을 새 키로 교체하면 됩니다."),
    ]

    for q, a in qas:
        q_tbl = Table(
            [[Paragraph(q, ParagraphStyle("qt", fontName="MalgunBd", fontSize=11,
                                           textColor=BLUE))]],
            colWidths=[W - 40*mm],
        )
        q_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), LIGHT_BLUE),
            ("LEFTPADDING",  (0, 0), (-1, -1), 10),
            ("TOPPADDING",   (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
        ]))
        a_tbl = Table(
            [[Paragraph(a, S["body_sm"])]],
            colWidths=[W - 40*mm],
        )
        a_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), WHITE),
            ("LEFTPADDING",  (0, 0), (-1, -1), 14),
            ("TOPPADDING",   (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
            ("LINEBELOW",    (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ]))
        story.append(q_tbl)
        story.append(a_tbl)
        story.append(sp(2))

    return story


# ── 페이지 번호 콜백 ─────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Malgun", 8)
    canvas.setFillColor(GRAY)
    canvas.drawCentredString(W / 2, 15*mm,
                              f"세금계산서 발행 도우미 사용 설명서  |  {doc.page}페이지")
    canvas.restoreState()


# ── 메인 ────────────────────────────────────────────────────────
def build(output_path: str = "세금계산서_발행도우미_사용설명서.pdf") -> None:
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=15*mm, bottomMargin=20*mm,
        title="세금계산서 발행 도우미 사용 설명서",
        author="내부 문서",
    )

    story: list = []
    story += cover_page()
    story += toc_page()
    story += section1()
    story += section2()
    story += section3()
    story += section4()
    story += section5()
    story += section6()
    story += section7()
    story += section8()
    story += section9()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF 생성 완료: {output_path}")


if __name__ == "__main__":
    build()

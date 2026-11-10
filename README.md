# 세금계산서 발행 도우미

엑셀로 정리한 세금계산서 명세를 한 행씩 검사해서 **발행 대기 · 거래처 보완 · 실패 · 중복 차단 · 발행 완료**로 나누는 주피터 노트북 도구입니다. 회계세무를 전공하며 세금계산서를 발행하기 전에 확인해야 할 것들을 코드로 정리해 본 개인 프로젝트입니다.

## 검사하는 것

| 검사 | 내용 | 결과 상태 |
|---|---|---|
| 필수 칸 | 작성일·거래처명·사업자번호·품목·공급가액·세액 등이 비어 있는지 | 실패 / 거래처 보완 |
| 사업자번호 | `XXX-XX-XXXXX` 형식, 키가 있으면 국세청 사업자등록 상태조회(공공데이터포털 API) | 실패 |
| 세액 | 과세 거래에서 **세액 = 공급가액 × 10%** 인지 | 실패 |
| 중복 발행 | 같은 내용의 행을 해시로 만든 키로 막음 | 중복 차단 |
| 기록 | 처리 결과를 `queue.csv`(발행 대기열)와 `audit.json`(감사 로그)으로 저장 | — |

API 키는 `SecretStr`로 감싸서 로그나 오류 메시지에 값이 찍히지 않게 했습니다(`tests/test_security.py`).

## 실행

```bash
pip install -r requirements.txt
jupyter notebook tax_invoice_internal_app.ipynb
```

노트북에서 `tax_invoice_sample_50.xlsx`(가상 거래 50건)를 올리면 행마다 상태와 오류가 표시됩니다. 국세청 상태조회까지 쓰려면 `.env.example`을 `.env`로 복사하고 공공데이터포털에서 받은 키를 넣습니다. 키가 없으면 형식 검사만 합니다.

## 테스트

```bash
python -m pytest tests/test_tax_invoice_domain.py tests/test_security.py
```

22개 테스트가 통과합니다(2026-11-10 확인). 상태 분류, 중복 차단, 100건 자체 점검 파일의 오류율 0%, 키 노출 방지를 확인합니다. `tests/integration_nts_verify.py`는 실제 API 키로 국세청 조회를 확인하는 수동 점검용입니다.

## 파일

| 파일 | 역할 |
|---|---|
| `tax_invoice_domain.py` | 템플릿 칸 정의, 행 검사, 상태 분류, 중복 키 |
| `tax_invoice_adapters.py` | 사업자번호 확인(형식 / 국세청 API), 발행 대기열 미리보기 |
| `tax_invoice_records.py` | 발행 대기열과 감사 로그 저장 |
| `tax_invoice_config.py` | `.env`에서 키 읽기, `SecretStr` |
| `tax_invoice_internal_app.py` · `.ipynb` | 노트북 화면(ipywidgets) |
| `write_manual_pdf.py` | 사용설명서 PDF 생성 → `세금계산서_발행도우미_사용설명서.pdf` |

## 한계

- 과세 거래만 다룹니다. 영세율·면세는 지원하지 않습니다.
- 실제 발행(홈택스·발행 대행 서비스) 연동은 없습니다. 발행 대기열을 만들어 보여 주는 데까지입니다.
- 화면이 주피터 위젯이라 웹으로 배포하지 않았습니다.
- 샘플 엑셀의 거래처와 사업자번호는 모두 가상입니다.

## 만든 방법

AI 코딩 도구(Claude Code)를 사용해 만들었습니다.

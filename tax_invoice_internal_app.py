from __future__ import annotations

from io import BytesIO

import ipywidgets as widgets
import pandas as pd
from IPython.display import display

from tax_invoice_adapters import QueuePreviewAdapter
from tax_invoice_domain import (
    REQUIRED_COLUMNS,
    STATUS_LABELS,
    TEMPLATE_VERSION,
    export_sample_excel,
    export_self_test_excel,
    make_sample_template,
    make_self_test_template,
    summarize_validation,
    validate_rows,
)
from tax_invoice_records import IssuanceLedger, LocalBatchArtifacts, LocalSampleFileStore

STATUS_COLORS = {
    "ready-to-send": "#166534",
    "needs-party": "#92400e",
    "failed": "#991b1b",
    "sent": "#1d4ed8",
    "draft": "#475569",
    "validated": "#0f766e",
}


def _build_style_block() -> str:
    return """
    <style>
      .ti-shell { font-family: Pretendard, Apple SD Gothic Neo, sans-serif; color: #e5e7eb; background: #0f172a; padding: 24px; border-radius: 24px; }
      .ti-header { display: flex; justify-content: space-between; gap: 20px; align-items: stretch; margin-bottom: 20px; }
      .ti-card { background: #111827; border: 1px solid #263245; border-radius: 18px; padding: 18px; }
      .ti-title { font-size: 30px; font-weight: 800; margin: 0 0 10px; }
      .ti-sub { color: #9ca3af; line-height: 1.6; margin: 0; }
      .ti-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 20px; }
      .ti-summary-label { display: block; color: #9ca3af; font-size: 12px; margin-bottom: 8px; }
      .ti-summary-value { font-size: 26px; font-weight: 800; }
      .ti-table { width: 100%; border-collapse: collapse; }
      .ti-table th, .ti-table td { text-align: left; padding: 12px 10px; border-bottom: 1px solid #243041; }
      .ti-table th { color: #93a4bb; font-size: 12px; }
      .ti-badge { display: inline-block; border-radius: 999px; padding: 6px 10px; font-size: 12px; font-weight: 700; color: white; }
      .ti-detail-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 16px; margin: 18px 0; }
      .ti-detail-grid dt { color: #93a4bb; font-size: 12px; margin-bottom: 4px; }
      .ti-detail-grid dd { margin: 0; font-weight: 600; word-break: break-all; }
      .ti-issues { background: #0b1220; border: 1px solid #243041; border-radius: 14px; padding: 14px; margin-top: 16px; }
      .ti-issues p { margin: 0 0 8px; font-weight: 700; }
      .ti-issues ul { margin: 0; padding-left: 18px; color: #fca5a5; line-height: 1.6; }
      .ti-empty { color: #86efac; }
      .ti-template { color: #cbd5e1; font-size: 13px; line-height: 1.6; }
      .ti-note { color: #94a3b8; font-size: 12px; margin-top: 8px; }
      .ti-layout { display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(340px, 0.9fr); gap: 18px; align-items: start; }
      .ti-sidebar { display: flex; flex-direction: column; gap: 16px; }
    </style>
    """


def _badge(status_code: str) -> str:
    color = STATUS_COLORS[status_code]
    return f'<span class="ti-badge" style="background:{color}">{STATUS_LABELS[status_code]}</span>'


def _summary_html(validated: pd.DataFrame) -> str:
    summary = summarize_validation(validated)
    cards = [
        ("총 건수", f"{len(validated)}건"),
        ("발행 대기", f'{summary["ready-to-send"]}건'),
        ("보완 필요", f'{summary["needs-party"]}건'),
        ("검증 실패", f'{summary["failed"]}건'),
    ]
    body = "".join(
        f'<div class="ti-card"><span class="ti-summary-label">{label}</span><strong class="ti-summary-value">{value}</strong></div>'
        for label, value in cards
    )
    return f'<div class="ti-grid">{body}</div>'


def _table_html(validated: pd.DataFrame) -> str:
    table_df = validated[["행", "거래구분", "거래처명", "품목", "합계금액", "상태코드"]].copy()
    table_df["합계금액"] = table_df["합계금액"].map(lambda value: f"{value:,.0f}원")
    table_df["상태"] = table_df["상태코드"].map(_badge)
    table_df = table_df.drop(columns=["상태코드"])
    return table_df.to_html(index=False, escape=False, classes=["ti-table"])


def _queue_html(queue_df: pd.DataFrame) -> str:
    visible = queue_df[["행", "큐상태", "설명", "어댑터"]].copy()
    return f'<div class="ti-card"><h3 style="margin-bottom:12px;">발행 큐 미리보기</h3>{visible.to_html(index=False, classes=["ti-table"])}</div>'


def _artifact_html(artifacts: LocalBatchArtifacts | None) -> str:
    if artifacts is None:
        return '<div class="ti-card"><p class="ti-sub">아직 저장된 로컬 파일이 없습니다.</p></div>'

    return f"""
    <div class="ti-card">
      <h3 style="margin-bottom:12px;">로컬 파일 저장 결과</h3>
      <dl class="ti-detail-grid">
        <div><dt>배치 폴더</dt><dd>{artifacts.batch_dir}</dd></div>
        <div><dt>검증 결과 CSV</dt><dd>{artifacts.validation_csv}</dd></div>
        <div><dt>큐 결과 CSV</dt><dd>{artifacts.queue_csv}</dd></div>
        <div><dt>감사 로그 JSON</dt><dd>{artifacts.audit_json}</dd></div>
      </dl>
      <div class="ti-issues">
        <p>저장 정책</p>
        <p class="ti-empty">현재는 샘플/테스트 데이터만 로컬 파일로 저장합니다.</p>
      </div>
    </div>
    """


def _detail_html(row: pd.Series | None, queue_row: pd.Series | None) -> str:
    if row is None:
        return '<div class="ti-card"><p class="ti-sub">선택된 행이 없습니다.</p></div>'

    issue_block = (
        '<p class="ti-empty">추가 보완 없이 발행 큐에 넣을 수 있는 상태입니다.</p>'
        if not row["이슈"]
        else "<ul>" + "".join(f"<li>{issue}</li>" for issue in row["이슈"]) + "</ul>"
    )

    queue_state = queue_row["큐상태"] if queue_row is not None else "미정"
    queue_message = queue_row["설명"] if queue_row is not None else "큐 계산 전"

    return f"""
    <div class="ti-card">
      <p class="ti-sub">선택 행</p>
      <h3 style="margin:4px 0 8px;">{row["행"]} · {row["거래처명"]}</h3>
      {_badge(row["상태코드"])}
      <dl class="ti-detail-grid">
        <div><dt>거래 구분</dt><dd>{row["거래구분"]}</dd></div>
        <div><dt>작성일</dt><dd>{row["작성일"]}</dd></div>
        <div><dt>사업자번호</dt><dd>{row["거래처사업자번호"] or "입력 필요"}</dd></div>
        <div><dt>품목</dt><dd>{row["품목"]}</dd></div>
        <div><dt>공급가액</dt><dd>{row["공급가액"]:,.0f}원</dd></div>
        <div><dt>세액</dt><dd>{row["세액"]:,.0f}원</dd></div>
        <div><dt>템플릿버전</dt><dd>{row["템플릿버전"]}</dd></div>
        <div><dt>멱등키</dt><dd>{row["멱등키"]}</dd></div>
        <div><dt>큐 상태</dt><dd>{queue_state}</dd></div>
        <div><dt>큐 설명</dt><dd>{queue_message}</dd></div>
      </dl>
      <div class="ti-issues">
        <p>검증 메모</p>
        {issue_block}
      </div>
    </div>
    """


def build_tax_invoice_notebook_app() -> None:
    adapter = QueuePreviewAdapter()
    ledger = IssuanceLedger()
    store = LocalSampleFileStore(base_dir="local_tax_invoice_data")

    profile_name = widgets.Text(value="내부 운영 계정", description="상호")
    profile_number = widgets.Text(value="123-45-67890", description="사업자번호")
    upload = widgets.FileUpload(accept=".xlsx,.xls", multiple=False, description="엑셀 업로드")
    load_sample = widgets.Button(description="50건 샘플 데이터 불러오기", button_style="primary")
    load_self_test = widgets.Button(description="100건 self-test 데이터 불러오기")
    reset = widgets.Button(description="초기화")
    filter_dropdown = widgets.Dropdown(
        options=[
            ("전체", "all"),
            ("발행 대기", "ready-to-send"),
            ("거래처 보완", "needs-party"),
            ("검증 실패", "failed"),
            ("발행 완료", "sent"),
        ],
        value="all",
        description="필터",
    )
    row_select = widgets.Select(description="행 선택", rows=12)

    header_html = widgets.HTML(
        value=f"""
        {_build_style_block()}
        <div class="ti-shell">
          <div class="ti-header">
            <div class="ti-card" style="flex:1.7">
              <p class="ti-sub" style="margin-bottom:6px;">내부 세금계산서 처리 프로그램</p>
              <h1 class="ti-title">업로드, 검증, 큐 생성 판단을 한 화면에서 처리하는 주피터 노트북 버전</h1>
              <p class="ti-sub">실제 발행 호출 대신, 발행 가능 행을 멱등키 기준으로 큐에 올릴 수 있는지 먼저 검토합니다.</p>
            </div>
            <div class="ti-card" style="flex:1">
              <strong>필수 컬럼</strong>
              <p class="ti-template">{", ".join(REQUIRED_COLUMNS)}</p>
              <p class="ti-note">템플릿버전은 {TEMPLATE_VERSION}이어야 합니다.</p>
            </div>
          </div>
        </div>
        """
    )

    summary_html = widgets.HTML()
    table_html = widgets.HTML()
    queue_html = widgets.HTML()
    artifact_html = widgets.HTML()
    detail_html = widgets.HTML()
    status_html = widgets.HTML()

    state = {
        "validated": pd.DataFrame(),
        "queue": pd.DataFrame(),
        "artifacts": None,
    }

    def refresh_view() -> None:
        validated = state["validated"]
        queue_df = state["queue"]
        if validated.empty:
            summary_html.value = ""
            table_html.value = '<div class="ti-card"><p class="ti-sub">먼저 샘플 데이터를 불러오거나 엑셀을 업로드해 주세요.</p></div>'
            queue_html.value = '<div class="ti-card"><p class="ti-sub">검증이 완료되면 발행 큐 미리보기가 표시됩니다.</p></div>'
            artifact_html.value = _artifact_html(None)
            detail_html.value = '<div class="ti-card"><p class="ti-sub">행을 선택하면 상세 검증 내용이 표시됩니다.</p></div>'
            row_select.options = []
            return

        visible = validated if filter_dropdown.value == "all" else validated[validated["상태코드"] == filter_dropdown.value]
        visible_ids = set(visible["행"])
        visible_queue = queue_df[queue_df["행"].isin(visible_ids)] if not queue_df.empty else queue_df

        summary_html.value = _summary_html(validated)
        table_html.value = f'<div class="ti-card"><h3 style="margin-bottom:12px;">행별 검토</h3>{_table_html(visible)}</div>'
        queue_html.value = _queue_html(visible_queue) if not visible_queue.empty else '<div class="ti-card"><p class="ti-sub">표시할 큐 데이터가 없습니다.</p></div>'
        artifact_html.value = _artifact_html(state["artifacts"])

        options = [
            (f'{row["행"]} | {row["거래처명"]} | {row["상태"]}', row["행"])
            for _, row in visible.iterrows()
        ]
        row_select.options = options

        selected_value = row_select.value
        valid_ids = {value for _, value in options}
        if options and selected_value not in valid_ids:
            row_select.value = options[0][1]

        selected_row = None
        selected_queue_row = None
        if row_select.value:
            selected = validated[validated["행"] == row_select.value]
            if not selected.empty:
                selected_row = selected.iloc[0]
            selected_queue = queue_df[queue_df["행"] == row_select.value]
            if not selected_queue.empty:
                selected_queue_row = selected_queue.iloc[0]

        detail_html.value = _detail_html(selected_row, selected_queue_row)

    def load_dataframe(dataframe: pd.DataFrame, source: str) -> None:
        validated = validate_rows(dataframe)
        queue_df = ledger.prepare_queue(validated, adapter)
        artifacts = store.save_batch(validated, queue_df, source)
        state["validated"] = validated
        state["queue"] = queue_df
        state["artifacts"] = artifacts

        summary = summarize_validation(validated)
        queued = int((queue_df["큐상태"] == "queued").sum())
        duplicates = int((queue_df["큐상태"] == "duplicate-blocked").sum())
        status_html.value = (
            f'<p class="ti-note">{source} · 총 {len(validated)}건 로드됨 · '
            f'발행 대기 {summary["ready-to-send"]} · 거래처 보완 {summary["needs-party"]} · '
            f'검증 실패 {summary["failed"]} · 발행 완료 {summary["sent"]} · '
            f'큐 적재 {queued} · 중복 차단 {duplicates} · 어댑터 {adapter.name} · '
            f'로컬 저장 {artifacts.batch_dir.name}</p>'
        )
        refresh_view()

    def on_load_sample(_: widgets.Button) -> None:
        load_dataframe(make_sample_template(), "샘플 데이터")

    def on_load_self_test(_: widgets.Button) -> None:
        load_dataframe(make_self_test_template(100), "100건 self-test 데이터")

    def on_reset(_: widgets.Button) -> None:
        state["validated"] = pd.DataFrame()
        state["queue"] = pd.DataFrame()
        state["artifacts"] = None
        status_html.value = '<p class="ti-note">상태가 초기화되었습니다.</p>'
        refresh_view()

    def on_filter_change(_: dict) -> None:
        refresh_view()

    def on_row_select(_: dict) -> None:
        refresh_view()

    def on_upload_change(change: dict) -> None:
        uploads = change["new"]
        if not uploads:
            return

        first_file = uploads[0] if isinstance(uploads, tuple) else next(iter(uploads.values()))
        content = first_file["content"]
        dataframe = pd.read_excel(BytesIO(content))
        load_dataframe(dataframe, f'업로드 파일: {first_file["name"]}')

    load_sample.on_click(on_load_sample)
    load_self_test.on_click(on_load_self_test)
    reset.on_click(on_reset)
    filter_dropdown.observe(on_filter_change, names="value")
    row_select.observe(on_row_select, names="value")
    upload.observe(on_upload_change, names="value")

    controls = widgets.VBox(
        [
            widgets.HBox([profile_name, profile_number]),
            widgets.HBox([upload, load_sample, load_self_test, reset, filter_dropdown]),
            status_html,
        ]
    )

    body = widgets.HBox(
        [
            widgets.VBox([summary_html, table_html, queue_html, artifact_html], layout=widgets.Layout(width="68%")),
            widgets.VBox([row_select, detail_html], layout=widgets.Layout(width="32%")),
        ],
        layout=widgets.Layout(width="100%"),
    )

    display(header_html)
    display(controls)
    display(body)

    refresh_view()


if __name__ == "__main__":
    print("Open tax_invoice_internal_app.ipynb in Jupyter and run the cells.")

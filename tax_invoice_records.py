from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path

import pandas as pd

from tax_invoice_adapters import IssuanceAdapter


@dataclass
class IssuanceLedger:
    existing_keys: set[str] = field(default_factory=set)

    def prepare_queue(self, validated: pd.DataFrame, adapter: IssuanceAdapter) -> pd.DataFrame:
        queue_rows: list[dict[str, object]] = []
        batch_seen: set[str] = set()

        for _, row in validated.iterrows():
            idempotency_key = row["멱등키"]

            if row["상태코드"] == "sent":
                self.existing_keys.add(idempotency_key)
                queue_rows.append(
                    {
                        "행": row["행"],
                        "큐상태": "already-sent",
                        "설명": "이미 발행 완료된 행입니다.",
                        "어댑터": adapter.name,
                    }
                )
                continue

            if row["상태코드"] != "ready-to-send":
                queue_rows.append(
                    {
                        "행": row["행"],
                        "큐상태": "blocked",
                        "설명": "검증 또는 거래처 보완이 끝나야 큐에 넣을 수 있습니다.",
                        "어댑터": adapter.name,
                    }
                )
                continue

            if idempotency_key in self.existing_keys or idempotency_key in batch_seen:
                queue_rows.append(
                    {
                        "행": row["행"],
                        "큐상태": "duplicate-blocked",
                        "설명": "동일 멱등키가 이미 존재해 중복 발행을 차단했습니다.",
                        "어댑터": adapter.name,
                    }
                )
                continue

            result = adapter.preview_issue(row)
            batch_seen.add(idempotency_key)
            queue_rows.append(
                {
                    "행": row["행"],
                    "큐상태": result.queue_state,
                    "설명": result.message,
                    "어댑터": adapter.name,
                }
            )

        return pd.DataFrame(queue_rows)


@dataclass(frozen=True)
class LocalBatchArtifacts:
    batch_dir: Path
    validation_csv: Path
    queue_csv: Path
    audit_json: Path


@dataclass
class LocalSampleFileStore:
    base_dir: Path | str = Path("local_tax_invoice_data")

    def __post_init__(self) -> None:
        self.base_dir = Path(self.base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_batch(
        self,
        validated: pd.DataFrame,
        queue_df: pd.DataFrame,
        source: str,
    ) -> LocalBatchArtifacts:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        batch_dir = self.base_dir / f"sample-batch-{timestamp}"
        batch_dir.mkdir(parents=True, exist_ok=False)

        validation_csv = batch_dir / "validated.csv"
        queue_csv = batch_dir / "queue.csv"
        audit_json = batch_dir / "audit.json"

        validated.to_csv(validation_csv, index=False, encoding="utf-8-sig")
        queue_df.to_csv(queue_csv, index=False, encoding="utf-8-sig")

        audit_payload = {
            "scope": "sample-test-only",
            "source": source,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "validated_rows": int(len(validated)),
            "queue_rows": int(len(queue_df)),
            "queue_state_counts": {
                str(key): int(value)
                for key, value in queue_df["큐상태"].value_counts().to_dict().items()
            }
            if not queue_df.empty
            else {},
        }
        audit_json.write_text(
            json.dumps(audit_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return LocalBatchArtifacts(
            batch_dir=batch_dir,
            validation_csv=validation_csv,
            queue_csv=queue_csv,
            audit_json=audit_json,
        )

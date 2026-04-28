"""Logging strutturato JSONL — un record per ogni tentativo di invio."""

import json
import os
from datetime import datetime


class StructuredLogger:
    def __init__(self, log_dir: str):
        os.makedirs(log_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        self.log_path = os.path.join(log_dir, f"session_{date_str}.jsonl")

    def log(self, **fields):
        record = {"timestamp": datetime.now().isoformat(), **fields}
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def log_attempt(self, platform: str, url: str, title: str,
                    status: str, reason: str = "", attempt: int = 1,
                    duration_ms: int = 0, screenshot: str = "",
                    html_snapshot: str = ""):
        self.log(
            event="attempt",
            platform=platform,
            url=url,
            title=title[:80],
            status=status,
            reason=reason,
            attempt=attempt,
            duration_ms=duration_ms,
            screenshot=screenshot,
            html_snapshot=html_snapshot,
        )

    def log_session(self, platform: str, event: str, **extra):
        self.log(event=event, platform=platform, **extra)

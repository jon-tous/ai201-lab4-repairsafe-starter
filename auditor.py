import json
import os
import uuid
from datetime import datetime, timezone
from config import LOG_FILE, LLM_MODEL


def log_interaction(question: str, tier: str, response: str) -> None:
    """
    Append a structured record of this interaction to the audit log.

    TODO — Milestone 3:

    Before writing any code, complete specs/auditor-spec.md. The key decisions
    are what fields to log, how much of the question and response to include,
    and how to handle the logs/ directory not existing yet.

    Each record should be a JSON object written as a single line to LOG_FILE
    (defined in config.py as "logs/audit.jsonl").

    Required fields:
      - "timestamp"        : ISO 8601 datetime string
      - "tier"             : the safety tier assigned to this question
      - "question"         : the user's question (truncate to 300 chars if longer)
      - "response_preview" : first 200 characters of the response

    If the logs/ directory doesn't exist, create it before writing.

    Also print a one-line summary to the terminal so you can see logged
    interactions in real time without opening the file:
      e.g. [LOGGED] tier=caution | "How do I replace a faucet?" → 47 chars

    Design your log entry in specs/auditor-spec.md before implementing here.
    """
    # Normalize and truncate fields
    q = (question or "").replace("\n", " ").strip()
    q_trunc = q if len(q) <= 300 else q[:300]

    resp = (response or "").replace("\n", " ").strip()
    resp_preview = resp if len(resp) <= 200 else resp[:200]
    resp_len = len(resp)

    # Additional fields for debugging / correlation
    record = {
      "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
      "tier": tier,
      "question": q_trunc,
      "response_preview": resp_preview,
      "llm_model": LLM_MODEL,
      "request_id": str(uuid.uuid4()),
    }

    # Ensure logs directory exists
    dirpath = os.path.dirname(LOG_FILE) or "logs"
    try:
      os.makedirs(dirpath, exist_ok=True)
    except OSError:
      # If we can't create the directory, print an error and skip logging
      print(f"[LOGGING ERROR] could not create logs directory: {dirpath}")
      return

    # Append JSON line to the log file
    try:
      with open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
      print(f"[LOGGING ERROR] could not write to log file: {LOG_FILE}")
      return

    # Console summary
    short_q = q_trunc if len(q_trunc) <= 80 else q_trunc[:77] + "..."
    print(
      f"[LOGGED] {record['timestamp']} | tier={tier} | question=\"{short_q}\" | response_preview=\"{resp_preview}\" (resp={resp_len} chars)"
    )

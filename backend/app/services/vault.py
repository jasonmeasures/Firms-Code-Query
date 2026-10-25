"""EDI vault: list, add, edit. Mirrors the 5106 vault rules for this extract app."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.edi.envelope import read_user_data, unbracket
from app.edi.rules import extract_rule_errors
from app.edi.view import annotate, infer_file_code, mq_envelope, normalize_and_validate_edi
from app.models import ExtractOrphan, ExtractRequest, User
from app.mq.outbound import ExtractOutbound
from app.security import can_see, visible_requests
from app.services.workflow import _log, mask_password, new_control_id

_SAFE_ITEM_ID = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


def _check_item_id(item_id: str) -> None:
    if not _SAFE_ITEM_ID.match(item_id) or ".." in item_id:
        raise HTTPException(status_code=404, detail="EDI not found")


def _outbox() -> Path:
    return ExtractOutbound().outbox


def _is_vault_scratch(row: ExtractRequest | None) -> bool:
    """Pasted vault EDI and orphan outbox files are not ACE extract queries."""
    return row is None or row.query_type in {"VAULT", "OUTBOX"}


def _blocks_rule_errors(row: ExtractRequest | None) -> bool:
    return not _is_vault_scratch(row)


def edit_lock_reason(row: ExtractRequest | None) -> str | None:
    if row is None:
        return None
    if row.mq_send_state == "SENT" and row.status in {"PENDING_CBP", "APPROVED", "REJECTED"}:
        return "This EDI is read-only after a successful send."
    return None


def _restore_password(edi: str, previous: str) -> str:
    settings = get_settings()
    lines = edi.split("\n")
    if not lines or not lines[0].startswith("A") or len(lines[0]) < 14:
        return edi
    incoming = lines[0][8:14]
    stored = previous.split("\n")[0][8:14] if previous.startswith("A") and len(previous.split("\n")[0]) >= 14 else settings.password.ljust(6)[:6]
    if incoming.strip() == "":
        lines[0] = lines[0][:8] + stored + lines[0][14:]
        return "\n".join(lines)
    if incoming != stored:
        raise HTTPException(status_code=422, detail=["Communication password cannot be changed in the vault"])
    return "\n".join(lines)


def _set_control(edi: str, control: str) -> str:
    lines = edi.split("\n")
    if len(lines) >= 2 and lines[1].startswith("B"):
        line = lines[1].ljust(80)
        lines[1] = line[:59] + control.ljust(21)[:21] + line[80:]
    return "\n".join(lines)


def _write_outbox(control_id: str, edi: str) -> None:
    settings = get_settings()
    if settings.mq_mode == "live":
        return
    folder = _outbox()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{control_id}.edi").write_text(
        "\n".join(f"[{line}]" for line in edi.split("\n") if line.strip()),
        encoding="utf-8",
    )


def _resolve(session: Session, user: User, item_id: str) -> tuple[ExtractRequest | None, str]:
    _check_item_id(item_id)
    row = session.get(ExtractRequest, item_id)
    if row is None:
        row = session.scalar(select(ExtractRequest).where(ExtractRequest.control_id == item_id.upper()))
    if row is not None:
        if not can_see(user, row):
            raise HTTPException(status_code=404, detail="EDI not found")
        return row, row.edi_text
    if user.role != "ADMIN":
        raise HTTPException(status_code=404, detail="EDI not found")
    path = _outbox() / f"{item_id}.edi"
    if path.exists():
        return None, unbracket(path.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="EDI not found")


def _item(row: ExtractRequest | None, item_id: str, edi: str, *, with_body: bool = False) -> dict:
    shown = mask_password(edi)
    control = row.control_id if row else item_id
    file_code = row.file_code if row else infer_file_code(edi) or "F111"
    filename = f"{control}.edi"
    payload = {
        "id": row.id if row else item_id,
        "filename": filename,
        "edi_filename": filename,
        "status": row.status if row else "OUTBOX",
        "action": file_code,
        "file_code": file_code,
        "query_type": row.query_type if row else "OUTBOX",
        "control_id": control,
        "kn_number": row.kn_number if row else "",
        "mq_send_state": row.mq_send_state if row else None,
        "mq_send_error": row.mq_send_error if row else None,
        "request_id": row.id if row else None,
        "editable": edit_lock_reason(row) is None,
        "edit_locked_reason": edit_lock_reason(row),
    }
    if with_body:
        payload.update({
            "edi": shown,
            "edi_raw": shown,
            "records": annotate(shown),
            "envelope": mq_envelope(
                edi=shown,
                file_code=file_code,
                control_id=control,
                filename=filename,
                request_id=row.id if row else "",
            ),
            "warnings": extract_rule_errors(edi),
        })
    return payload


def list_vault(session: Session, user: User) -> dict:
    rows = session.scalars(visible_requests(user).limit(200)).all()
    filings = [_item(row, row.id, row.edi_text) for row in rows if row.edi_text]
    outbox_items = []
    unmatched = []
    if user.role == "ADMIN":
        known = {row.control_id for row in rows}
        folder = _outbox()
        if folder.exists():
            for path in sorted(folder.glob("*.edi"), reverse=True):
                if path.stem in known:
                    continue
                edi = unbracket(path.read_text(encoding="utf-8"))
                outbox_items.append(_item(None, path.stem, edi))
        orphans = session.scalars(select(ExtractOrphan).order_by(ExtractOrphan.received_at.desc()).limit(100)).all()
        unmatched = [
            {
                "id": item.id,
                "control_id": item.control_id,
                "kn_number": item.kn_number,
                "raw_text": item.raw_text,
                "received_at": item.received_at.isoformat() if item.received_at else None,
            }
            for item in orphans
        ]
    failed = [row for row in rows if row.mq_send_state == "FAILED"]
    return {
        "filings": filings,
        "outbox": outbox_items,
        "requests": filings,
        "orphans": unmatched,
        "dead_letters": [_item(row, row.id, row.edi_text) for row in failed] if user.role == "ADMIN" else [],
    }


def check_edi(raw: str) -> dict:
    edi, errors = normalize_and_validate_edi(raw)
    rule_errors = extract_rule_errors(edi or raw)
    records = annotate(edi or raw)
    return {
        "ok": not errors and not rule_errors,
        "errors": errors,
        "rule_errors": rule_errors,
        "edi": edi if not errors else raw,
        "records": records,
        "line_count": len(records),
        "all_80": bool(records) and all(rec["ok"] for rec in records),
    }


def get_item(session: Session, user: User, item_id: str) -> dict:
    row, edi = _resolve(session, user, item_id)
    return _item(row, item_id, edi, with_body=True)


def add_item(session: Session, user: User, raw: str) -> dict:
    edi, errors = normalize_and_validate_edi(raw)
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    edi = _restore_password(edi, "")
    kn, control, _app = read_user_data(edi)
    control = (control or "").strip().upper() or new_control_id()
    if session.scalar(select(ExtractRequest).where(ExtractRequest.control_id == control)):
        raise HTTPException(status_code=409, detail="That control ID is already used. Generate another.")
    edi = _set_control(edi, control)
    file_code = infer_file_code(edi) or "F111"
    row = ExtractRequest(
        control_id=control,
        kn_number=kn,
        file_code=file_code,
        query_type="VAULT",
        params={"source": "vault"},
        edi_text=edi,
        status="DRAFT",
        requested_by=user.id,
    )
    session.add(row)
    session.flush()
    _log(session, row, "DRAFT", user.id, "EDI added in vault")
    session.commit()
    session.refresh(row)
    return _item(row, row.id, row.edi_text, with_body=True)


def edit_item(session: Session, user: User, item_id: str, raw: str) -> dict:
    row, previous = _resolve(session, user, item_id)
    locked = edit_lock_reason(row)
    if locked:
        raise HTTPException(status_code=409, detail=locked)
    edi, errors = normalize_and_validate_edi(raw)
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    edi = _restore_password(edi, previous)
    _, old_control, _ = read_user_data(previous)
    _, new_control, _ = read_user_data(edi)
    if old_control and new_control and old_control != new_control:
        raise HTTPException(status_code=422, detail=["Control ID cannot be changed in the vault"])
    rule_errors = extract_rule_errors(edi)
    if rule_errors and _blocks_rule_errors(row):
        raise HTTPException(status_code=422, detail=rule_errors)
    if row:
        old_hash = hashlib.sha256((row.edi_text or "").encode()).hexdigest()[:12]
        new_hash = hashlib.sha256(edi.encode()).hexdigest()[:12]
        row.edi_text = edi
        _log(session, row, row.status, user.id, f"EDI edited in vault ({old_hash} -> {new_hash})")
        _write_outbox(row.control_id, edi)
        session.commit()
        session.refresh(row)
        return _item(row, row.id, row.edi_text, with_body=True)
    path = _outbox() / f"{item_id}.edi"
    path.write_text("\n".join(f"[{line}]" for line in edi.split("\n") if line.strip()), encoding="utf-8")
    return _item(None, item_id, edi, with_body=True)


def download_text(session: Session, user: User, item_id: str) -> tuple[str, str]:
    item = get_item(session, user, item_id)
    return item["filename"], item["edi"]

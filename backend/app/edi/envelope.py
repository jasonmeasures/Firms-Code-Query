"""A/B/Y/Z block for extract queries. This is not the 5106 TP envelope."""

from __future__ import annotations

from dataclasses import dataclass

from app.edi.layout import (
    A_APP,
    A_DATE,
    A_KN,
    A_PASSWORD,
    A_SENDER,
    A_SITE,
    B_APP,
    B_CONTROL,
    B_FILER,
    B_PORT,
    B_PREPARER_FILER,
    B_PREPARER_FLAG,
    B_PREPARER_PORT,
    Y_APP,
    Y_FILER,
    Y_PORT,
    Z_DATE,
    Z_SENDER,
    Z_SITE,
    blank,
    freeze,
    place,
)


@dataclass(frozen=True)
class Identity:
    site_code: str
    sender_id: str
    password: str
    port: str
    filer: str
    preparer_port: str = ""
    preparer_filer: str = ""

    def check(self) -> None:
        if len(self.site_code) != 4 or len(self.port) != 4:
            raise ValueError("Site code and port must be 4 characters")
        if len(self.sender_id) != 3 or len(self.filer) != 3:
            raise ValueError("Sender id and filer must be 3 characters")
        if len(self.password) != 6:
            raise ValueError("Communication password must be 6 characters")


def record_a(identity: Identity, when: str, app_id: str, kn_number: str, *, blank_password: bool = False) -> str:
    buf = blank()
    place(buf, (1, 1), "A")
    place(buf, A_SITE, identity.site_code)
    place(buf, A_SENDER, identity.sender_id)
    place(buf, A_PASSWORD, "" if blank_password else identity.password)
    place(buf, A_DATE, when)
    place(buf, A_APP, app_id)
    place(buf, A_KN, kn_number)
    return freeze(buf)


def record_b(
    identity: Identity,
    app_id: str,
    control_id: str,
    *,
    preparer: bool = True,
) -> str:
    buf = blank()
    place(buf, (1, 1), "B")
    place(buf, B_PORT, identity.port)
    place(buf, B_FILER, identity.filer)
    place(buf, B_APP, app_id)
    if preparer:
        place(buf, B_PREPARER_PORT, identity.preparer_port or identity.port)
        place(buf, B_PREPARER_FILER, identity.preparer_filer or identity.filer)
        place(buf, B_PREPARER_FLAG, "1")
    place(buf, B_CONTROL, control_id)
    return freeze(buf)


def record_y(identity: Identity, app_id: str) -> str:
    buf = blank()
    place(buf, (1, 1), "Y")
    place(buf, Y_PORT, identity.port)
    place(buf, Y_FILER, identity.filer)
    place(buf, Y_APP, app_id)
    return freeze(buf)


def record_z(identity: Identity, when: str) -> str:
    buf = blank()
    place(buf, (1, 1), "Z")
    place(buf, Z_SITE, identity.site_code)
    place(buf, Z_SENDER, identity.sender_id)
    place(buf, Z_DATE, when)
    return freeze(buf)


def wrap_block(
    identity: Identity,
    when: str,
    app_id: str,
    kn_number: str,
    control_id: str,
    queries: list[str],
) -> str:
    identity.check()
    if not queries:
        raise ValueError("A block needs at least one query record")
    lines = [
        record_a(identity, when, app_id, kn_number),
        record_b(identity, app_id, control_id, preparer=True),
        *queries,
        record_y(identity, app_id),
        record_z(identity, when),
    ]
    return "\n".join(lines)


def unbracket(edi: str) -> str:
    """Drop optional brackets and pad each record to 80. Trailing spaces are padding."""
    from app.edi.layout import RECORD_LEN

    out: list[str] = []
    for ln in (edi or "").replace("\r\n", "\n").split("\n"):
        if not ln.strip():
            continue
        text = ln.strip()
        if text.startswith("[") and text.endswith("]"):
            text = text[1:-1]
        out.append(text[:RECORD_LEN].ljust(RECORD_LEN))
    return "\n".join(out)


def read_user_data(edi: str) -> tuple[str, str, str]:
    """Return (A user data, control ID, application id) from the A and B records."""
    from app.edi.layout import A_KN, B_APP, B_CONTROL, take

    lines = [ln for ln in unbracket(edi).split("\n") if ln.strip()]
    if len(lines) < 2 or lines[0][:1] != "A" or lines[1][:1] != "B":
        return "", "", ""
    return take(lines[0], A_KN), take(lines[1], B_CONTROL), take(lines[1], B_APP)


def bracket(edi: str) -> str:
    return "\n".join(f"[{ln}]" for ln in edi.split("\n") if ln.strip())

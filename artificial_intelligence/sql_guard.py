import re

_FENCE = re.compile(r"```(?:sql)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)
_COMMENT_LINE = re.compile(r"--[^\n]*")
_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE|MERGE|GRANT|REVOKE|INTO)\b",
    re.IGNORECASE,
)


def extract_sql(raw: str) -> str:
    """Isola o comando SQL quando o modelo devolve cerca ou texto ao redor."""
    if not isinstance(raw, str):
        raise ValueError("O modelo não devolveu um comando SQL.")

    text = raw.strip()
    if text.upper().startswith("ERRO"):
        raise ValueError(text)

    fenced = _FENCE.findall(text)
    if fenced:
        text = fenced[0].strip()

    match = re.search(r"\b(WITH|SELECT)\b", text, re.IGNORECASE)
    if match:
        text = text[match.start():]

    return text.strip().rstrip(";").strip()


def is_read_query(sql: str) -> bool:
    """Aceita um único SELECT ou WITH ... SELECT, sem escrita nem segundo comando."""
    cleaned = _COMMENT_BLOCK.sub(" ", sql)
    cleaned = _COMMENT_LINE.sub(" ", cleaned).strip()
    if not cleaned or ";" in cleaned:
        return False

    head = cleaned.lstrip().upper()
    if not (head.startswith("SELECT") or head.startswith("WITH")):
        return False

    return _FORBIDDEN.search(cleaned) is None

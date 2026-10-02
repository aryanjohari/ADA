"""Operator-written site file. A wake does not create this file or fill a field."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from ada.io.paths import DataPaths, require_ada_data
from ada.memory import blog_packet
from ada.memory.campaign_page import SITE, one_sentence

PUBLIC_HOST = "https://aryan-portfolio-one-kappa.vercel.app"
AIMS = frozenset({"hire", "prove-shipping", "educate", "book", "call"})
PORTFOLIO_AIMS = frozenset({"hire", "prove-shipping", "educate"})
ACTION_KINDS = frozenset({"replies", "bookings", "calls"})
CTA_LABEL = "Get in touch"
_KEYWORD_FIELDS = frozenset({"keyword", "keywords"})
_QUERY_FIELDS = frozenset({"query", "queries"})
_CONSOLE_FIELDS = frozenset(
    {"clicks", "impressions", "ctr", "average_position", "averageposition"}
)
_REQUIRED = (
    "site",
    "audience",
    "aim",
    "places",
    "offer",
    "proof",
    "contact",
    "actions",
    "folders",
)


def _deny(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "outcome": "denied",
        "denied_reason": reason,
        "error": reason,
    }


def _http_label(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"https", "mailto"} and bool(parsed.path or parsed.netloc)


def _field_name(key: object) -> str:
    return str(key).casefold().replace(" ", "").replace("-", "").replace("_", "")


def _banned_field(node: Any) -> str | None:
    """A keyword, a query, or a Search Console number stored as a field."""
    if isinstance(node, dict):
        for key, value in node.items():
            name = _field_name(key)
            if name in _KEYWORD_FIELDS or name == "keyword":
                return "refusing a keyword field"
            if name in _QUERY_FIELDS or name == "query":
                return "refusing a query field"
            if name in _CONSOLE_FIELDS:
                return "refusing a search console field"
            found = _banned_field(value)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _banned_field(item)
            if found:
                return found
    return None


def _string_list(value: Any, field: str) -> list[str] | dict[str, Any]:
    if not isinstance(value, list):
        return _deny(f"{field} must be a list")
    cleaned: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            return _deny(f"{field} must be a list")
        cleaned.append(item.strip())
    return cleaned


def _read_cta(raw: dict[str, Any], config: dict[str, Any]) -> dict[str, Any] | None:
    """Optional mail-and-call pair the later stages already read. Both or neither."""
    if "default_cta" not in raw or raw.get("default_cta") in (None, "absent"):
        config["default_cta"] = None
        return None
    cta = raw.get("default_cta")
    if not isinstance(cta, dict):
        return _deny("call to action needs both a mail URL and a call URL")
    label = str(cta.get("label") or "").strip()
    mail = str(cta.get("mail") or "").strip()
    call = str(cta.get("call") or "").strip()
    if label != CTA_LABEL:
        return _deny("call to action label must be Get in touch")
    if not mail or not call:
        return _deny("call to action needs both a mail URL and a call URL")
    if not _http_label(mail) or not _http_label(call):
        return _deny("call to action needs both a mail URL and a call URL")
    config["default_cta"] = {"label": CTA_LABEL, "mail": mail, "call": call}
    return None


def _read_folders(raw_folders: Any) -> list[str] | dict[str, Any]:
    """Card folders. Each one is a path inside this repo.

    There is no per-row sentence, question, source, or url. The operator
    does not write the title and does not refill a list of 12.
    """
    if not isinstance(raw_folders, list):
        return _deny("folders must be a list")
    root = blog_packet.repo_root().resolve()
    folders: list[str] = []
    for item in raw_folders:
        if isinstance(item, dict):
            return _deny("a folder is a path")
        if not isinstance(item, str) or not item.strip():
            return _deny("a folder is a path")
        text = item.strip().replace("\\", "/").strip("/")
        if not text or text.endswith(".md") or "://" in text:
            return _deny("a folder is a path")
        parts = Path(text).parts
        if not parts or ".." in parts or text.startswith("/"):
            return _deny("a folder is a path inside this repo")
        try:
            (root / text).resolve().relative_to(root)
        except ValueError:
            return _deny("a folder is a path inside this repo")
        if text not in folders:
            folders.append(text)
    return folders


def read_portfolio_chain(*, paths: DataPaths | None = None) -> dict[str, Any]:
    """Read the operator YAML. Write nothing. Fill nothing that is missing.

    One site, one audience sentence, one aim, and the card folders.
    Audience is who the reader is, not a topic. A folder is a path inside
    this repo. Proof may be an empty list. There is no fact list and no
    per-row sentence, question, source, or url.
    ``book`` and ``call`` are valid on a record whose site is not the portfolio.
    This function does not publish that record.
    """
    p = paths or require_ada_data()
    path = p.portfolio_chain_yaml
    if not path.is_file():
        return _deny("portfolio chain config is missing")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return _deny("portfolio chain config is missing")
    banned = _banned_field(raw)
    if banned:
        return _deny(banned)
    if "facts" in raw:
        return _deny("facts is not a field")
    if "sites" in raw or isinstance(raw.get("site"), (list, dict)):
        return _deny("refusing a second site")
    for key in _REQUIRED:
        if key not in raw:
            return _deny(f"missing field {key}")
    if "aims" in raw or isinstance(raw.get("aim"), (list, tuple)):
        return _deny("two aims")
    site = raw.get("site")
    if not isinstance(site, str) or not site.strip():
        return _deny("refusing a second site")
    site = site.strip()
    audience = raw.get("audience")
    if not isinstance(audience, str) or not one_sentence(audience):
        return _deny("audience must be one sentence")
    aim = raw.get("aim")
    if not isinstance(aim, str) or aim.strip() not in AIMS:
        return _deny("aim must be one of hire, prove-shipping, educate, book, or call")
    aim = aim.strip()
    places = _string_list(raw.get("places"), "places")
    if isinstance(places, dict):
        return places
    offer = raw.get("offer")
    if not isinstance(offer, str):
        return _deny("offer must be a string")
    proof = _string_list(raw.get("proof"), "proof")
    if isinstance(proof, dict):
        return proof
    contact = raw.get("contact")
    if not isinstance(contact, str):
        return _deny("contact must be a string")
    actions = raw.get("actions")
    if not isinstance(actions, dict):
        return _deny("actions needs kind and count")
    kind = actions.get("kind")
    count = actions.get("count")
    if not isinstance(kind, str) or kind.strip() not in ACTION_KINDS:
        return _deny("actions.kind must be replies, bookings, or calls")
    kind = kind.strip()
    if isinstance(count, bool) or not isinstance(count, int):
        return _deny("actions.count must be an integer")
    portfolio = site == SITE
    if portfolio:
        if aim not in PORTFOLIO_AIMS:
            return _deny("aim must not be book or call on the portfolio")
        if places:
            return _deny("places on the portfolio must be empty")
        if kind != "replies":
            return _deny("portfolio actions.kind is replies")
        show_contact = aim == "hire"
    else:
        if kind not in {"bookings", "calls"}:
            return _deny("actions.kind must be bookings or calls")
        show_contact = True
    folders = _read_folders(raw.get("folders"))
    if isinstance(folders, dict):
        return folders
    branch_raw = raw.get("branch", "main")
    if not isinstance(branch_raw, str) or not branch_raw.strip() or "/" in branch_raw or ".." in branch_raw:
        return _deny("branch is missing")
    config: dict[str, Any] = {
        "site": site,
        "audience": audience.strip(),
        "aim": aim,
        "aims": [aim],
        "places": places,
        "offer": offer.strip(),
        "proof": proof,
        "contact": contact.strip(),
        "show_contact": show_contact,
        "actions": {"kind": kind, "count": count},
        "folders": folders,
        "branch": branch_raw.strip(),
    }
    cta_error = _read_cta(raw, config)
    if cta_error:
        return cta_error
    return {"ok": True, "outcome": "ok", "config": config}

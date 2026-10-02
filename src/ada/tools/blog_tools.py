"""Blog page sidecar and portfolio checkout tools."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from ada.io.atomic import atomic_write_text
from ada.io.paths import DataPaths, require_ada_data
from ada.memory.blog_draft import replace_frontmatter_dates, utc_calendar_day
from ada.memory.blog_slug import SlugError, require_blog_segment
from ada.memory.campaign_page import (
    SITE,
    next_wake_iso,
    read_page,
    upsert_campaign_page,
    write_page,
)
from ada.memory.open_loops import get_loop, upsert_loop

ENV_CHECKOUT = "ADA_PORTFOLIO_CHECKOUT"
_ORIGIN_MARK = "aryanjohari/aryan-portfolio"


class CheckoutError(ValueError):
    """ADA_PORTFOLIO_CHECKOUT is unset, missing, or not the portfolio repo."""


def _deny(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "outcome": "denied",
        "denied_reason": reason,
        "error": reason,
    }


def _needs_confirm(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "needs_confirm": True,
        "outcome": "needs_confirm",
        "reason": reason,
    }


def _read_git_config(checkout: Path) -> str:
    git = checkout / ".git"
    if git.is_file():
        line = git.read_text(encoding="utf-8").strip()
        if not line.startswith("gitdir:"):
            raise CheckoutError("ADA_PORTFOLIO_CHECKOUT is not a git checkout")
        gitdir = Path(line.split(":", 1)[1].strip())
        if not gitdir.is_absolute():
            gitdir = (checkout / gitdir).resolve()
        config = gitdir / "config"
    elif git.is_dir():
        config = git / "config"
    else:
        raise CheckoutError("ADA_PORTFOLIO_CHECKOUT is not a git checkout")
    if not config.is_file():
        raise CheckoutError("ADA_PORTFOLIO_CHECKOUT is not a git checkout")
    return config.read_text(encoding="utf-8")


def _origin_url(config_text: str) -> str:
    in_origin = False
    for line in config_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_origin = stripped == '[remote "origin"]'
            continue
        if in_origin and stripped.startswith("url") and "=" in stripped:
            return stripped.split("=", 1)[1].strip()
    return ""


def resolve_portfolio_checkout() -> Path:
    """Existing git checkout whose origin URL contains the portfolio repo.

    No home directory is hardcoded. An unset variable, a missing directory,
    or a different remote is a refusal.
    """
    raw = os.environ.get(ENV_CHECKOUT, "")
    if not raw.strip():
        raise CheckoutError("ADA_PORTFOLIO_CHECKOUT is unset")
    path = Path(raw).expanduser().resolve()
    if not path.is_dir():
        raise CheckoutError("ADA_PORTFOLIO_CHECKOUT is missing")
    if not (path / ".git").exists():
        raise CheckoutError("ADA_PORTFOLIO_CHECKOUT is not a git checkout")
    origin = _origin_url(_read_git_config(path))
    if _ORIGIN_MARK not in origin:
        raise CheckoutError("origin is not aryanjohari/aryan-portfolio")
    return path


def blog_dest(checkout: Path, slug: str) -> Path:
    """Only ``{checkout}/content/blog/{slug}.md``. ``..`` and a slash refuse."""
    require_blog_segment(slug)
    root = checkout.resolve()
    blog_dir = root / "content" / "blog"
    dest = (blog_dir / f"{slug}.md").resolve()
    dest.relative_to(blog_dir.resolve())
    if dest.parent != blog_dir.resolve():
        raise SlugError("slug is not one path segment")
    return dest


def blog_media_dest(checkout: Path, slug: str, ext: str) -> Path:
    """Only ``{checkout}/content/blog/media/{slug}.webp`` or ``.svg``."""
    require_blog_segment(slug)
    if ext not in {".webp", ".svg"}:
        raise SlugError("media extension refused")
    root = checkout.resolve()
    media = root / "content" / "blog" / "media"
    dest = (media / f"{slug}{ext}").resolve()
    dest.relative_to(media.resolve())
    if dest.parent != media.resolve():
        raise SlugError("slug is not one path segment")
    return dest


def _artifact_file(paths: DataPaths, receipt: str) -> Path:
    rel = (receipt or "").strip().replace("\\", "/")
    if not rel.startswith("artifacts/") or ".." in rel.split("/"):
        raise ValueError("draft receipt is not under artifacts/")
    root = paths.artifacts.resolve()
    target = (root / rel[len("artifacts/") :]).resolve()
    target.relative_to(root)
    if not target.is_file():
        raise ValueError("draft receipt file is missing")
    return target


def _ready_page(
    campaign_id: str,
    paths: DataPaths,
) -> tuple[dict[str, Any], dict[str, Any]] | dict[str, Any]:
    page = read_page(campaign_id, paths=paths)
    loop = get_loop(campaign_id, paths=paths)
    if page is None or loop is None:
        return _deny("campaign page is missing")
    if str(page.get("site") or "") != SITE:
        return _deny(f"site must be {SITE}")
    return page, loop


def run_blog_page_upsert(args: dict[str, Any]) -> dict[str, Any]:
    return upsert_campaign_page(
        site=args.get("site"),
        audience=args.get("audience"),
        source=args.get("source"),
        question=args.get("question"),
        fill=args.get("fill"),
        cta_label=args.get("cta_label"),
        cta_url=args.get("cta_url"),
        campaign_id=args.get("campaign_id"),
    )


def _critic_pass(campaign_id: str, paths: DataPaths) -> dict[str, Any] | None:
    from ada.memory.chain_receipt import latest_receipt

    return latest_receipt(campaign_id, "critic", outcome="pass", paths=paths)


def _advance_chain(campaign_id: str, stage: str, paths: DataPaths) -> None:
    from ada.memory.chain_plan import CHAIN_STAGES, _rewrite_stages, is_chain_loop
    from ada.memory.open_loops import get_loop

    loop = get_loop(campaign_id, paths=paths)
    if not is_chain_loop(loop):
        upsert_loop(loop_id=campaign_id, next_wake_at=next_wake_iso(), paths=paths)
        return
    if str(loop.get("current_stage") or "") != stage:
        return
    idx = CHAIN_STAGES.index(stage)
    nxt = CHAIN_STAGES[idx + 1] if idx + 1 < len(CHAIN_STAGES) else stage
    _rewrite_stages(
        campaign_id,
        paths=paths,
        current=nxt,
        done={stage},
        active=nxt if nxt != stage else None,
        status="active",
    )


def run_blog_checkout_write(args: dict[str, Any]) -> dict[str, Any]:
    """Copy the draft into this origin. Does not read confirmed."""
    cid = str(args.get("campaign_id") or "").strip()
    if not cid:
        return _deny("campaign_id required")
    paths = require_ada_data()
    try:
        checkout = resolve_portfolio_checkout()
    except CheckoutError as exc:
        return _deny(str(exc))
    ready = _ready_page(cid, paths)
    if isinstance(ready, dict) and ready.get("ok") is False:
        return ready
    page, loop = ready
    from ada.memory.chain_plan import is_chain_loop

    if is_chain_loop(loop) and str(loop.get("current_stage") or "") != "deliver":
        return _deny("deliver is not the current stage")
    passed = _critic_pass(cid, paths)
    if passed is None:
        return _deny("critic has not passed")
    if passed.get("deliver_block"):
        return _deny("content/blog slug already exists")
    slug = str(page.get("slug") or passed.get("slug") or "")
    try:
        require_blog_segment(slug)
        dest = blog_dest(checkout, slug)
    except (SlugError, ValueError, OSError) as exc:
        return _deny(str(exc))
    if dest.exists():
        return _deny(f"content/blog/{slug}.md already exists")
    artifact_paths = [str(item) for item in (passed.get("paths") or [])]
    md_rel = next((item for item in artifact_paths if item.endswith(".md")), "")
    if not md_rel:
        return _deny("critic has not passed")
    try:
        draft = _artifact_file(paths, md_rel)
    except (ValueError, OSError) as exc:
        return _deny(str(exc))
    day = utc_calendar_day()
    try:
        stamped = replace_frontmatter_dates(draft.read_text(encoding="utf-8"), day)
    except (OSError, ValueError) as exc:
        return _deny(str(exc))
    media_rel = next(
        (item for item in artifact_paths if item.endswith(".svg") or item.endswith(".webp")),
        "",
    )
    media_dest: Path | None = None
    media_bytes: bytes | None = None
    if media_rel:
        try:
            staged = _artifact_file(paths, media_rel)
            ext = staged.suffix
            media_dest = blog_media_dest(checkout, slug, ext)
        except (SlugError, ValueError, OSError) as exc:
            return _deny(str(exc))
        if media_dest.exists():
            return _deny(f"content/blog/media/{slug}{media_dest.suffix} already exists")
        media_bytes = staged.read_bytes()
        if b"unsplash.com" in media_bytes.lower():
            return _deny("refusing an Unsplash or hotlinked image")
    atomic_write_text(dest, stamped)
    written = [f"content/blog/{slug}.md"]
    if media_dest is not None and media_bytes is not None:
        media_dest.parent.mkdir(parents=True, exist_ok=True)
        media_dest.write_bytes(media_bytes)
        written.append(f"content/blog/media/{slug}{media_dest.suffix}")
    from ada.memory.chain_receipt import append_stage_receipt

    append_stage_receipt(
        cid,
        {
            "stage": "deliver",
            "slug": slug,
            "outcome": "ok",
            "paths": written,
        },
        paths=paths,
    )
    _advance_chain(cid, "deliver", paths)
    return {
        "ok": True,
        "outcome": "ok",
        "path": str(dest),
        "paths": written,
        "slug": slug,
        "published": day,
        "modified": day,
    }


def run_blog_checkout_delete(args: dict[str, Any]) -> dict[str, Any]:
    """Remove the checkout file and clear the slug. Question and fill stay."""
    cid = str(args.get("campaign_id") or "").strip()
    if not cid:
        return _deny("campaign_id required")
    paths = require_ada_data()
    page = read_page(cid, paths=paths)
    if page is None:
        return _deny("campaign page is missing")
    if str(page.get("site") or "") != SITE:
        return _deny(f"site must be {SITE}")
    slug = str(page.get("slug") or "")
    try:
        require_blog_segment(slug)
        checkout = resolve_portfolio_checkout()
        dest = blog_dest(checkout, slug)
    except (CheckoutError, SlugError, ValueError, OSError) as exc:
        return _deny(str(exc))
    if not bool(args.get("confirmed", False)):
        return _needs_confirm("blog_checkout_delete requires confirmed=true")
    if not dest.is_file():
        return _deny(f"content/blog/{slug}.md is absent")
    dest.unlink()
    stored = dict(page)
    stored["slug"] = ""
    write_page(cid, stored, paths=paths)
    upsert_loop(
        loop_id=cid,
        status="active",
        next_wake_at=next_wake_iso(),
        paths=paths,
    )
    return {"ok": True, "outcome": "ok", "slug": "", "deleted": str(dest)}


def commit_argv(message: str) -> list[str]:
    return [
        "git",
        "-c",
        "user.email=ada@localhost",
        "-c",
        "user.name=ADA",
        "commit",
        "-m",
        message,
    ]


def push_argv(branch: str) -> list[str]:
    """Push the current commit. No --force, no --no-verify, no amend."""
    return ["git", "push", "origin", f"HEAD:{branch}"]


def _porcelain(checkout: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=checkout,
        check=True,
        capture_output=True,
        text=True,
    )
    found: list[str] = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        entry = line[3:].strip()
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1].strip()
        found.append(entry)
    return found


def _allowed_rel(path: str, slug: str) -> bool:
    parts = path.split("/")
    if not path or path.startswith("/") or ".." in parts:
        return False
    return path == f"content/blog/{slug}.md" or path in {
        f"content/blog/media/{slug}.svg",
        f"content/blog/media/{slug}.webp",
    }


def run_blog_checkout_push(args: dict[str, Any]) -> dict[str, Any]:
    """Commit and push only the deliver paths. The SHA is not campaign done."""
    cid = str(args.get("campaign_id") or "").strip()
    if not cid:
        return _deny("campaign_id required")
    paths = require_ada_data()
    try:
        checkout = resolve_portfolio_checkout()
    except CheckoutError as exc:
        return _deny(str(exc))
    ready = _ready_page(cid, paths)
    if isinstance(ready, dict) and ready.get("ok") is False:
        return ready
    page, loop = ready
    from ada.memory.chain_plan import is_chain_loop
    from ada.memory.chain_receipt import append_stage_receipt, latest_receipt
    from ada.memory.portfolio_chain import read_portfolio_chain

    if is_chain_loop(loop) and str(loop.get("current_stage") or "") != "push":
        return _deny("push is not the current stage")
    delivered = latest_receipt(cid, "deliver", outcome="ok", paths=paths)
    if delivered is None:
        return _deny("deliver has not written a receipt")
    slug = str(page.get("slug") or delivered.get("slug") or "")
    try:
        require_blog_segment(slug)
    except SlugError as exc:
        return _deny(str(exc))
    allowed = [str(item) for item in (delivered.get("paths") or [])]
    if not allowed or any(not _allowed_rel(item, slug) for item in allowed):
        return _deny("deliver receipt path is outside content/blog")
    config = read_portfolio_chain(paths=paths)
    if not config.get("ok"):
        return config
    branch = str(config["config"]["branch"])
    try:
        dirty = _porcelain(checkout)
    except (OSError, subprocess.CalledProcessError) as exc:
        return _deny(str(exc))
    if set(dirty) != set(allowed):
        return _deny("refusing a path outside the deliver receipt")
    add = ["git", "add", "--", *allowed]
    commit = commit_argv(f"Publish content/blog/{slug}.md")
    push = push_argv(branch)
    for argv in (add, commit, push):
        if "--force" in argv or "--no-verify" in argv or "--amend" in argv:
            return _deny("refusing force, amend, or skipped hooks")
    try:
        subprocess.run(add, cwd=checkout, check=True, capture_output=True, text=True)
        cached = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=checkout,
            check=True,
            capture_output=True,
            text=True,
        )
        names = [line.strip() for line in cached.stdout.splitlines() if line.strip()]
        if set(names) != set(allowed):
            return _deny("refusing a path outside the deliver receipt")
        subprocess.run(commit, cwd=checkout, check=True, capture_output=True, text=True)
        subprocess.run(push, cwd=checkout, check=True, capture_output=True, text=True)
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=checkout,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        return _deny(str(exc))
    append_stage_receipt(
        cid,
        {
            "stage": "push",
            "slug": slug,
            "outcome": "ok",
            "paths": allowed,
            "sha": sha,
        },
        paths=paths,
    )
    _advance_chain(cid, "push", paths)
    loop_after = get_loop(cid, paths=paths) or {}
    if loop_after.get("status") == "done":
        return _deny("refusing to mark the campaign done from the commit SHA")
    return {
        "ok": True,
        "outcome": "ok",
        "sha": sha,
        "slug": slug,
        "paths": allowed,
        "status": loop_after.get("status"),
    }


def run_blog_chain_wake(args: dict[str, Any]) -> dict[str, Any]:
    from ada.memory.chain_plan import run_chain_wake

    return run_chain_wake(str(args.get("campaign_id") or ""))


DISPATCH = {
    "blog_page_upsert": run_blog_page_upsert,
    "blog_checkout_write": run_blog_checkout_write,
    "blog_checkout_delete": run_blog_checkout_delete,
    "blog_checkout_push": run_blog_checkout_push,
    "blog_chain_wake": run_blog_chain_wake,
}

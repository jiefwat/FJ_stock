#!/usr/bin/env python3
"""Small admin app for the docs.jiewat-kaka-fj.com file center."""

from __future__ import annotations

# ruff: noqa: E501, I001

import argparse
import cgi
import html
import json
import mimetypes
import os
import re
import shutil
import sys
import tempfile
import time
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


APP_PREFIX = "/file-center"
API_PREFIX = "/api/file-center"
DEFAULT_GROUP_ID = "inbox"
SITE_ROOT_GROUP_ID = "site-root"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".csv",
    ".gif",
    ".htm",
    ".html",
    ".jpeg",
    ".jpg",
    ".json",
    ".md",
    ".pdf",
    ".png",
    ".svg",
    ".txt",
    ".webp",
    ".xlsx",
}
ALLOWED_URL_SCHEMES = {"http", "https"}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slugify(value: str, fallback: str = "item") -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return slug or fallback


def safe_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型：{ext or '无后缀'}")
    return ext


def public_url_for(group_id: str, filename: str) -> str:
    if group_id == SITE_ROOT_GROUP_ID:
        return f"/{filename}"
    return f"/files/{group_id}/{filename}"


def target_dir_for_group(config: FileCenterConfig, group_id: str) -> Path:
    if group_id == SITE_ROOT_GROUP_ID:
        return config.public_root
    return config.files_root / group_id


def unique_filename(directory: Path, original_name: str) -> str:
    ext = safe_extension(original_name)
    stem = Path(original_name).stem
    base = slugify(stem, fallback="page")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = f"{base}-{stamp}{ext}"
    counter = 2
    while (directory / candidate).exists():
        candidate = f"{base}-{stamp}-{counter}{ext}"
        counter += 1
    return candidate


@dataclass(frozen=True)
class FileCenterConfig:
    public_root: Path
    data_root: Path
    host: str
    port: int

    @property
    def files_root(self) -> Path:
        return self.public_root / "files"

    @property
    def manifest_path(self) -> Path:
        return self.data_root / "manifest.json"


class FileCenterStore:
    def __init__(self, config: FileCenterConfig):
        self.config = config
        self.config.public_root.mkdir(parents=True, exist_ok=True)
        self.config.files_root.mkdir(parents=True, exist_ok=True)
        self.config.data_root.mkdir(parents=True, exist_ok=True)
        self._ensure_manifest()

    def _ensure_manifest(self) -> None:
        if self.config.manifest_path.exists():
            return
        self._write(
            {
                "version": 1,
                "groups": {
                    DEFAULT_GROUP_ID: {
                        "id": DEFAULT_GROUP_ID,
                        "name": "默认收件箱",
                        "created_at": now_iso(),
                    },
                    SITE_ROOT_GROUP_ID: {
                        "id": SITE_ROOT_GROUP_ID,
                        "name": "站点根目录",
                        "created_at": now_iso(),
                        "system": True,
                    },
                },
                "files": [],
            }
        )

    def _read(self) -> dict[str, Any]:
        with self.config.manifest_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def _write(self, manifest: dict[str, Any]) -> None:
        fd, tmp_name = tempfile.mkstemp(
            prefix=".manifest-", suffix=".json", dir=self.config.data_root
        )
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp_name, self.config.manifest_path)

    def state(self) -> dict[str, Any]:
        self._sync_public_files()
        manifest = self._read()
        groups = sorted(
            manifest.get("groups", {}).values(), key=lambda group: group.get("created_at", "")
        )
        files = sorted(
            manifest.get("files", []), key=lambda item: item.get("uploaded_at", ""), reverse=True
        )
        counts: dict[str, int] = {group["id"]: 0 for group in groups}
        for file_item in files:
            counts[file_item["group_id"]] = counts.get(file_item["group_id"], 0) + 1
        return {"groups": groups, "files": files, "counts": counts}

    def _sync_public_files(self) -> None:
        """Register static files that were published outside the file-center API."""
        manifest = self._read()
        groups = manifest.setdefault("groups", {})
        files = manifest.setdefault("files", [])
        changed = False

        if SITE_ROOT_GROUP_ID not in groups:
            groups[SITE_ROOT_GROUP_ID] = {
                "id": SITE_ROOT_GROUP_ID,
                "name": "站点根目录",
                "created_at": now_iso(),
                "system": True,
            }
            changed = True

        known_urls = {entry.get("url") for entry in files}
        for path in sorted(self.config.public_root.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            if path.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue
            relative_path = path.relative_to(self.config.public_root)
            if any(part.startswith(".") for part in relative_path.parts):
                continue
            group_id = self._group_id_for_public_path(relative_path, groups)
            if group_id not in groups:
                groups[group_id] = {
                    "id": group_id,
                    "name": self._group_name_for_public_path(relative_path),
                    "created_at": now_iso(),
                    "system": True,
                }
                changed = True
            url = "/" + relative_path.as_posix()
            if url in known_urls:
                continue
            stat = path.stat()
            files.append(
                {
                    "id": uuid.uuid4().hex,
                    "kind": "file",
                    "title": path.name,
                    "filename": path.name,
                    "group_id": group_id,
                    "url": url,
                    "size": stat.st_size,
                    "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                    "uploaded_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                    .astimezone()
                    .isoformat(timespec="seconds"),
                    "updated_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                    .astimezone()
                    .isoformat(timespec="seconds"),
                    "source": "public-scan",
                }
            )
            known_urls.add(url)
            changed = True

        if changed:
            self._write(manifest)

    def _group_id_for_public_path(self, relative_path: Path, groups: dict[str, Any]) -> str:
        parts = relative_path.parts
        if len(parts) == 1:
            return SITE_ROOT_GROUP_ID
        if parts[0] == "files" and len(parts) >= 3:
            return parts[1]
        directory = "/".join(parts[:-1])
        group_id = f"dir-{slugify(directory, fallback='directory')}"
        if group_id in groups:
            return group_id
        return group_id

    def _group_name_for_public_path(self, relative_path: Path) -> str:
        parts = relative_path.parts
        if len(parts) == 1:
            return "站点根目录"
        if parts[0] == "files" and len(parts) >= 3:
            return parts[1]
        return "/".join(parts[:-1])

    def add_group(self, name: str) -> dict[str, Any]:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("分组名称不能为空")
        manifest = self._read()
        groups = manifest.setdefault("groups", {})
        base = slugify(clean_name, fallback="group")
        group_id = base
        if group_id in groups:
            group_id = f"{base}-{int(time.time())}"
        group = {"id": group_id, "name": clean_name, "created_at": now_iso()}
        groups[group_id] = group
        (self.config.files_root / group_id).mkdir(parents=True, exist_ok=True)
        self._write(manifest)
        return group

    def ensure_group(self, group_id: str) -> dict[str, Any]:
        manifest = self._read()
        groups = manifest.get("groups", {})
        if group_id not in groups:
            raise ValueError("目标分组不存在")
        return groups[group_id]

    def upload_file(
        self,
        *,
        group_id: str,
        original_name: str,
        file_obj: Any,
        content_type: str,
    ) -> dict[str, Any]:
        self.ensure_group(group_id)
        target_dir = target_dir_for_group(self.config, group_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = unique_filename(target_dir, original_name)
        target = target_dir / filename
        size = 0
        with target.open("wb") as out:
            while True:
                chunk = file_obj.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    target.unlink(missing_ok=True)
                    raise ValueError("单个文件不能超过 50MB")
                out.write(chunk)

        item = {
            "id": uuid.uuid4().hex,
            "kind": "file",
            "title": Path(original_name).name,
            "filename": filename,
            "group_id": group_id,
            "url": public_url_for(group_id, filename),
            "size": size,
            "content_type": content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
            "uploaded_at": now_iso(),
            "updated_at": now_iso(),
        }
        manifest = self._read()
        manifest.setdefault("files", []).append(item)
        self._write(manifest)
        return item

    def add_link(self, *, group_id: str, title: str, url: str) -> dict[str, Any]:
        self.ensure_group(group_id)
        clean_title = title.strip()
        clean_url = url.strip()
        parsed = urlparse(clean_url)
        if parsed.scheme not in ALLOWED_URL_SCHEMES or not parsed.netloc:
            raise ValueError("链接必须是 http 或 https 地址")
        item = {
            "id": uuid.uuid4().hex,
            "kind": "link",
            "title": clean_title or clean_url,
            "group_id": group_id,
            "url": clean_url,
            "size": 0,
            "content_type": "text/uri-list",
            "uploaded_at": now_iso(),
            "updated_at": now_iso(),
        }
        manifest = self._read()
        manifest.setdefault("files", []).append(item)
        self._write(manifest)
        return item

    def move_file(self, file_id: str, target_group_id: str) -> dict[str, Any]:
        self.ensure_group(target_group_id)
        manifest = self._read()
        files = manifest.get("files", [])
        item = next((entry for entry in files if entry.get("id") == file_id), None)
        if item is None:
            raise ValueError("文件不存在")
        if item.get("kind") == "link":
            item["group_id"] = target_group_id
            item["updated_at"] = now_iso()
            self._write(manifest)
            return item
        source = self.config.public_root / item["url"].lstrip("/")
        if not source.exists():
            raise ValueError("实体文件不存在，移动已取消")
        target_dir = target_dir_for_group(self.config, target_group_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = item["filename"]
        target = target_dir / filename
        if target.exists():
            filename = unique_filename(target_dir, filename)
            target = target_dir / filename
        shutil.move(str(source), str(target))
        item["group_id"] = target_group_id
        item["filename"] = filename
        item["url"] = public_url_for(target_group_id, filename)
        item["updated_at"] = now_iso()
        self._write(manifest)
        return item


class FileCenterHandler(BaseHTTPRequestHandler):
    store: FileCenterStore

    server_version = "JiewatFileCenter/1.0"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        sys.stderr.write(
            f"{self.address_string()} - - [{self.log_date_time_string()}] {format % args}\n"
        )

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {APP_PREFIX, f"{APP_PREFIX}/"}:
            self._send_html(render_app_html())
            return
        if path == f"{API_PREFIX}/state":
            self._send_json({"ok": True, **self.store.state()})
            return
        self._send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == f"{API_PREFIX}/groups":
                payload = self._read_json()
                group = self.store.add_group(str(payload.get("name", "")))
                self._send_json({"ok": True, "group": group})
                return
            if path == f"{API_PREFIX}/move":
                payload = self._read_json()
                item = self.store.move_file(
                    str(payload.get("file_id", "")), str(payload.get("target_group_id", ""))
                )
                self._send_json({"ok": True, "file": item})
                return
            if path == f"{API_PREFIX}/upload":
                items = self._handle_upload()
                self._send_json({"ok": True, "files": items})
                return
            if path == f"{API_PREFIX}/links":
                payload = self._read_json()
                item = self.store.add_link(
                    group_id=str(payload.get("group_id", DEFAULT_GROUP_ID)),
                    title=str(payload.get("title", "")),
                    url=str(payload.get("url", "")),
                )
                self._send_json({"ok": True, "file": item})
                return
        except ValueError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except Exception as exc:  # pragma: no cover - defensive for live admin use.
            self._send_json({"ok": False, "error": f"服务器处理失败：{exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self._send_error(HTTPStatus.NOT_FOUND, "Not found")

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1024 * 1024:
            raise ValueError("请求体过大")
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8") or "{}")

    def _handle_upload(self) -> list[dict[str, Any]]:
        ctype = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ctype:
            raise ValueError("请使用 multipart/form-data 上传")
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": ctype,
                "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
            },
        )
        group_id = str(form.getfirst("group_id", DEFAULT_GROUP_ID))
        self.store.ensure_group(group_id)
        fields = form["files"] if "files" in form else []
        if not isinstance(fields, list):
            fields = [fields]
        uploaded: list[dict[str, Any]] = []
        for field in fields:
            if not getattr(field, "filename", None):
                continue
            uploaded.append(
                self.store.upload_file(
                    group_id=group_id,
                    original_name=unquote(field.filename),
                    file_obj=field.file,
                    content_type=field.type,
                )
            )
        if not uploaded:
            raise ValueError("没有收到文件")
        return uploaded

    def _send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        escaped = html.escape(message)
        self._send_html(f"<!doctype html><title>{status.value}</title><p>{escaped}</p>", status=status)


def render_app_html() -> str:
    return r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="robots" content="noindex,nofollow" />
  <title>文件中台</title>
  <style>
    :root {
      --bg: #f6f7f8;
      --card: #ffffff;
      --ink: #1f2933;
      --muted: #6b7280;
      --line: #e5e7eb;
      --active: #14532d;
      --active-bg: #e8f5ec;
      --danger: #b42318;
      --radius: 12px;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "Avenir Next", "PingFang SC", "Microsoft YaHei", sans-serif;
      font-size: 14px;
    }
    button, input, select { font: inherit; }
    a { color: var(--active); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .page { max-width: 1120px; margin: 0 auto; padding: 24px 16px 40px; }
    .topbar { display: flex; justify-content: space-between; gap: 16px; align-items: center; margin-bottom: 16px; }
    h1 { margin: 0; font-size: 24px; line-height: 1.2; }
    .sub { color: var(--muted); margin-top: 4px; }
    .layout { display: grid; grid-template-columns: 230px 1fr; gap: 16px; }
    .card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); }
    .folders { padding: 12px; position: sticky; top: 16px; }
    .folder-title { color: var(--muted); font-weight: 700; margin: 4px 6px 10px; }
    .folder { width: 100%; display: flex; justify-content: space-between; gap: 10px; border: 0; background: transparent; color: var(--ink); padding: 10px 12px; border-radius: 10px; cursor: pointer; text-align: left; }
    .folder:hover, .folder.active, .folder.drag-over { background: var(--active-bg); color: var(--active); }
    .folder small { color: var(--muted); }
    .main { display: grid; gap: 12px; }
    .actions { padding: 14px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .box { border: 1px solid var(--line); border-radius: 10px; padding: 12px; display: grid; gap: 10px; align-content: start; }
    .box h2 { margin: 0; font-size: 15px; }
    .row { display: grid; grid-template-columns: 110px 1fr; gap: 10px; align-items: center; }
    label { color: var(--muted); }
    input, select { width: 100%; border: 1px solid var(--line); border-radius: 10px; padding: 9px 10px; background: #fff; color: var(--ink); }
    .button { border: 0; border-radius: 10px; padding: 9px 12px; background: var(--ink); color: #fff; cursor: pointer; }
    .button.secondary { background: var(--active); }
    .button.light { background: #eef2f7; color: var(--ink); }
    .toolbar { padding: 12px 14px; display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: center; }
    .status { min-height: 20px; color: var(--active); }
    .status.error { color: var(--danger); }
    .table { overflow: hidden; }
    .head, .file-row { display: grid; grid-template-columns: minmax(220px, 1.4fr) minmax(140px, .8fr) 120px 180px; gap: 12px; align-items: center; padding: 12px 14px; }
    .head { color: var(--muted); font-size: 12px; font-weight: 700; border-bottom: 1px solid var(--line); }
    .file-row { border-bottom: 1px solid var(--line); background: #fff; }
    .file-row:last-child { border-bottom: 0; }
    .file-row:hover { background: #fbfcfd; }
    .file-row[draggable="true"] { cursor: grab; }
    .name strong { display: block; overflow-wrap: anywhere; }
    .name small, .meta { color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
    .actions-cell { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    .actions-cell select { min-width: 130px; padding: 7px 8px; }
    .empty { padding: 28px 14px; text-align: center; color: var(--muted); }
    .new-folder { display: flex; gap: 8px; margin-top: 12px; }
    .new-folder input { min-width: 0; }
    @media (max-width: 860px) {
      .layout, .actions { grid-template-columns: 1fr; }
      .folders { position: static; }
      .head { display: none; }
      .file-row { grid-template-columns: 1fr; gap: 8px; }
      .row { grid-template-columns: 1fr; }
      .topbar { align-items: flex-start; flex-direction: column; }
    }
  </style>
</head>
<body>
  <main class="page">
    <header class="topbar">
      <div>
        <h1>文件中台</h1>
        <div class="sub">放文件、放链接、按文件夹查看。</div>
      </div>
      <button class="button light" id="refresh" type="button">刷新</button>
    </header>

    <section class="layout">
      <aside class="card folders">
        <div class="folder-title">文件夹</div>
        <div id="folderList"></div>
        <form id="groupForm" class="new-folder">
          <input id="groupName" name="name" type="text" placeholder="新文件夹" />
          <button class="button secondary" type="submit">新建</button>
        </form>
      </aside>

      <section class="main">
        <div class="card actions">
          <form id="uploadForm" class="box">
            <h2>上传文件</h2>
            <div class="row"><label for="uploadGroup">放到</label><select id="uploadGroup" name="group_id"></select></div>
            <div class="row"><label for="files">文件</label><input id="files" name="files" type="file" multiple accept=".html,.htm,.pdf,.md,.txt,.csv,.json,.png,.jpg,.jpeg,.webp,.svg,.gif,.xlsx" /></div>
            <button class="button" type="submit">上传</button>
          </form>

          <form id="linkForm" class="box">
            <h2>添加链接</h2>
            <div class="row"><label for="linkGroup">放到</label><select id="linkGroup" name="group_id"></select></div>
            <div class="row"><label for="linkTitle">名称</label><input id="linkTitle" name="title" type="text" placeholder="可不填" /></div>
            <div class="row"><label for="linkUrl">URL</label><input id="linkUrl" name="url" type="url" placeholder="https://..." required /></div>
            <button class="button" type="submit">保存链接</button>
          </form>
        </div>

        <div class="card toolbar">
          <input id="search" type="text" placeholder="搜索文件或链接" />
          <div id="status" class="status" role="status"></div>
        </div>

        <div class="card table">
          <div class="head"><span>名称</span><span>位置 / 类型</span><span>更新时间</span><span>操作</span></div>
          <div id="fileList"></div>
        </div>
      </section>
    </section>
  </main>

  <script>
    const state = { groups: [], files: [], counts: {}, activeGroup: 'all', dragging: null };
    const statusEl = document.getElementById('status');
    const folderListEl = document.getElementById('folderList');
    const fileListEl = document.getElementById('fileList');
    const uploadGroupEl = document.getElementById('uploadGroup');
    const linkGroupEl = document.getElementById('linkGroup');
    const searchEl = document.getElementById('search');

    function setStatus(message, isError = false) {
      statusEl.textContent = message || '';
      statusEl.classList.toggle('error', isError);
    }
    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    }
    function bytes(size) {
      if (!size) return '-';
      if (size < 1024) return size + ' B';
      if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB';
      return (size / 1024 / 1024).toFixed(1) + ' MB';
    }
    function absoluteUrl(url) {
      return /^https?:\/\//.test(url) ? url : new URL(url, window.location.origin).href;
    }
    async function api(path, options = {}) {
      const res = await fetch('/api/file-center' + path, options);
      const data = await res.json();
      if (!res.ok || data.ok === false) throw new Error(data.error || '请求失败');
      return data;
    }
    async function loadState() {
      const data = await api('/state');
      state.groups = data.groups || [];
      state.files = data.files || [];
      state.counts = data.counts || {};
      render();
    }
    function groupName(id) {
      return (state.groups.find(group => group.id === id) || {}).name || id;
    }
    function groupOptions(selected) {
      return state.groups.map(group => `<option value="${escapeHtml(group.id)}" ${group.id === selected ? 'selected' : ''}>${escapeHtml(group.name)}</option>`).join('');
    }
    function visibleFiles() {
      const q = searchEl.value.trim().toLowerCase();
      return state.files.filter(file => state.activeGroup === 'all' || file.group_id === state.activeGroup).filter(file => {
        if (!q) return true;
        return `${file.title} ${file.url}`.toLowerCase().includes(q);
      });
    }
    function render() {
      uploadGroupEl.innerHTML = groupOptions(uploadGroupEl.value || 'inbox');
      linkGroupEl.innerHTML = groupOptions(linkGroupEl.value || uploadGroupEl.value || 'inbox');
      const total = state.files.length;
      folderListEl.innerHTML = `<button class="folder ${state.activeGroup === 'all' ? 'active' : ''}" data-group="all"><span>全部</span><small>${total}</small></button>` + state.groups.map(group => `<button class="folder ${state.activeGroup === group.id ? 'active' : ''}" data-group="${escapeHtml(group.id)}"><span>${escapeHtml(group.name)}</span><small>${state.counts[group.id] || 0}</small></button>`).join('');
      const files = visibleFiles();
      fileListEl.innerHTML = files.length ? files.map(renderFile).join('') : '<div class="empty">这里还没有内容。上传文件，或者添加一个 URL。</div>';
      bindEvents();
    }
    function renderFile(file) {
      const isLink = file.kind === 'link';
      const typeText = isLink ? '链接' : `${escapeHtml(file.content_type || '文件')} · ${bytes(file.size || 0)}`;
      return `<div class="file-row" draggable="true" data-file-id="${escapeHtml(file.id)}">
        <div class="name"><strong>${escapeHtml(file.title)}</strong><small>${escapeHtml(absoluteUrl(file.url))}</small></div>
        <div class="meta">${escapeHtml(groupName(file.group_id))}<br>${typeText}</div>
        <div class="meta">${escapeHtml(file.updated_at || file.uploaded_at || '-')}</div>
        <div class="actions-cell">
          <a href="${escapeHtml(file.url)}" target="_blank" rel="noopener">打开</a>
          <a href="#" data-copy="${escapeHtml(file.url)}">复制</a>
          <select data-move-select="${escapeHtml(file.id)}">${groupOptions(file.group_id)}</select>
        </div>
      </div>`;
    }
    function bindEvents() {
      document.querySelectorAll('.folder').forEach(folder => {
        folder.addEventListener('click', () => { state.activeGroup = folder.dataset.group; render(); });
        if (folder.dataset.group !== 'all') {
          folder.addEventListener('dragover', event => { event.preventDefault(); folder.classList.add('drag-over'); });
          folder.addEventListener('dragleave', () => folder.classList.remove('drag-over'));
          folder.addEventListener('drop', async event => {
            event.preventDefault();
            folder.classList.remove('drag-over');
            await moveFile(event.dataTransfer.getData('text/plain') || state.dragging, folder.dataset.group);
          });
        }
      });
      document.querySelectorAll('.file-row').forEach(row => {
        row.addEventListener('dragstart', event => {
          state.dragging = row.dataset.fileId;
          event.dataTransfer.setData('text/plain', state.dragging);
        });
      });
      document.querySelectorAll('[data-move-select]').forEach(select => {
        select.addEventListener('change', async () => moveFile(select.dataset.moveSelect, select.value));
      });
      document.querySelectorAll('[data-copy]').forEach(link => {
        link.addEventListener('click', async event => {
          event.preventDefault();
          const url = absoluteUrl(link.dataset.copy);
          await navigator.clipboard.writeText(url);
          setStatus('已复制');
        });
      });
    }
    async function moveFile(fileId, targetGroupId) {
      if (!fileId || !targetGroupId) return;
      await api('/move', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({file_id: fileId, target_group_id: targetGroupId}) });
      setStatus('已移动');
      await loadState();
    }
    document.getElementById('uploadForm').addEventListener('submit', async event => {
      event.preventDefault();
      const formEl = event.currentTarget;
      try {
        setStatus('上传中...');
        await api('/upload', { method: 'POST', body: new FormData(formEl) });
        formEl.reset();
        setStatus('已上传');
        await loadState();
      } catch (error) {
        setStatus(error.message, true);
      }
    });
    document.getElementById('linkForm').addEventListener('submit', async event => {
      event.preventDefault();
      const formEl = event.currentTarget;
      try {
        const form = new FormData(formEl);
        await api('/links', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(Object.fromEntries(form.entries())) });
        formEl.reset();
        setStatus('链接已保存');
        await loadState();
      } catch (error) {
        setStatus(error.message, true);
      }
    });
    document.getElementById('groupForm').addEventListener('submit', async event => {
      event.preventDefault();
      const formEl = event.currentTarget;
      try {
        const name = document.getElementById('groupName').value;
        await api('/groups', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name}) });
        formEl.reset();
        setStatus('文件夹已创建');
        await loadState();
      } catch (error) {
        setStatus(error.message, true);
      }
    });
    document.getElementById('refresh').addEventListener('click', loadState);
    searchEl.addEventListener('input', render);
    loadState().catch(error => setStatus(error.message, true));
  </script>
</body>
</html>
"""

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Jiewat docs file center")
    parser.add_argument("--public-root", default="/opt/jiewat-docs/public")
    parser.add_argument("--data-root", default="/opt/jiewat-docs/data")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8721)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = FileCenterConfig(
        public_root=Path(args.public_root).resolve(),
        data_root=Path(args.data_root).resolve(),
        host=args.host,
        port=args.port,
    )
    FileCenterHandler.store = FileCenterStore(config)
    server = ThreadingHTTPServer((config.host, config.port), FileCenterHandler)
    print(f"file center listening on http://{config.host}:{config.port}{APP_PREFIX}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

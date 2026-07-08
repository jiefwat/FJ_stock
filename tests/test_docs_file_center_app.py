from __future__ import annotations

from io import BytesIO

from scripts.docs_file_center_app import FileCenterConfig, FileCenterStore


def test_file_center_uploads_to_selected_group(tmp_path):
    store = FileCenterStore(
        FileCenterConfig(
            public_root=tmp_path / "public",
            data_root=tmp_path / "data",
            host="127.0.0.1",
            port=0,
        )
    )

    group = store.add_group("客户方案")
    item = store.upload_file(
        group_id=group["id"],
        original_name="方案页.html",
        file_obj=BytesIO(b"<!doctype html><title>demo</title>"),
        content_type="text/html",
    )

    assert item["group_id"] == group["id"]
    assert item["url"].startswith(f"/files/{group['id']}/")
    assert (tmp_path / "public" / item["url"].lstrip("/")).exists()


def test_file_center_moves_page_between_groups(tmp_path):
    store = FileCenterStore(
        FileCenterConfig(
            public_root=tmp_path / "public",
            data_root=tmp_path / "data",
            host="127.0.0.1",
            port=0,
        )
    )
    first_group = store.add_group("初稿")
    second_group = store.add_group("正式")
    item = store.upload_file(
        group_id=first_group["id"],
        original_name="report.html",
        file_obj=BytesIO(b"hello"),
        content_type="text/html",
    )

    moved = store.move_file(item["id"], second_group["id"])

    assert moved["group_id"] == second_group["id"]
    assert moved["url"].startswith(f"/files/{second_group['id']}/")
    assert not (tmp_path / "public" / item["url"].lstrip("/")).exists()
    assert (tmp_path / "public" / moved["url"].lstrip("/")).exists()


def test_file_center_adds_and_moves_url_links(tmp_path):
    store = FileCenterStore(
        FileCenterConfig(
            public_root=tmp_path / "public",
            data_root=tmp_path / "data",
            host="127.0.0.1",
            port=0,
        )
    )
    first_group = store.add_group("链接")
    second_group = store.add_group("归档")

    item = store.add_link(
        group_id=first_group["id"],
        title="项目文档",
        url="https://docs.jiewat-kaka-fj.com/",
    )
    moved = store.move_file(item["id"], second_group["id"])

    assert item["kind"] == "link"
    assert moved["group_id"] == second_group["id"]
    assert moved["url"] == "https://docs.jiewat-kaka-fj.com/"


def test_file_center_indexes_existing_public_root_files(tmp_path):
    public_root = tmp_path / "public"
    public_root.mkdir()
    (public_root / "message-platform-simple.html").write_text(
        "<!doctype html><title>message</title>",
        encoding="utf-8",
    )
    store = FileCenterStore(
        FileCenterConfig(
            public_root=public_root,
            data_root=tmp_path / "data",
            host="127.0.0.1",
            port=0,
        )
    )

    first_state = store.state()
    second_state = store.state()

    indexed = [
        item for item in first_state["files"] if item["url"] == "/message-platform-simple.html"
    ]
    assert len(indexed) == 1
    assert indexed[0]["group_id"] == "site-root"
    assert first_state["counts"]["site-root"] == 1
    assert len(second_state["files"]) == len(first_state["files"])


def test_file_center_uploads_to_site_root_group(tmp_path):
    store = FileCenterStore(
        FileCenterConfig(
            public_root=tmp_path / "public",
            data_root=tmp_path / "data",
            host="127.0.0.1",
            port=0,
        )
    )
    store.state()

    item = store.upload_file(
        group_id="site-root",
        original_name="root-page.html",
        file_obj=BytesIO(b"root"),
        content_type="text/html",
    )

    assert item["url"].startswith("/root-page-")
    assert (tmp_path / "public" / item["url"].lstrip("/")).exists()

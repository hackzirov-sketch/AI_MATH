import os
import tempfile
import time
from pathlib import Path

from hypothesis import given, strategies as st

from services.cache_manager import CacheManager, CachePolicy, SafeCleanerWorker


def _make_manager(root: Path) -> CacheManager:
    return CacheManager(
        root_dir=root,
        policies={
            "renders": CachePolicy("renders", "renders", ttl_seconds=3600, max_size_mb=1),
            "pdf_temp": CachePolicy("pdf_temp", "pdf_temp", ttl_seconds=3600, max_size_mb=1),
            "tmp": CachePolicy("tmp", "tmp", ttl_seconds=3600, max_size_mb=1),
        },
    )


def _touch_old(path: Path, age_seconds: int = 7200) -> None:
    old_time = time.time() - age_seconds
    os.utime(path, (old_time, old_time))


def test_cleanup_deletes_only_allowed_expired_files(tmp_path: Path):
    manager = _make_manager(tmp_path / "cache_root")
    old_png = manager.get_cache_dir("renders") / "old.png"
    old_png.write_bytes(b"png-data")
    _touch_old(old_png)

    old_py = manager.get_cache_dir("renders") / "keep.py"
    old_py.write_text("print('keep')", encoding="utf-8")
    _touch_old(old_py)

    report = manager.cleanup_directory("renders", ttl_seconds=0, max_size_mb=1)

    assert not old_png.exists()
    assert old_py.exists()
    assert report.deleted_files == 1
    assert report.reason_counts["ttl_expired"] == 1


def test_cleanup_respects_size_limit_oldest_first(tmp_path: Path):
    manager = _make_manager(tmp_path / "cache_root")
    render_dir = manager.get_cache_dir("renders")

    oldest = render_dir / "oldest.png"
    middle = render_dir / "middle.png"
    newest = render_dir / "newest.png"

    oldest.write_bytes(b"a" * 420_000)
    middle.write_bytes(b"b" * 420_000)
    newest.write_bytes(b"c" * 420_000)

    now = time.time()
    os.utime(oldest, (now - 300, now - 300))
    os.utime(middle, (now - 200, now - 200))
    os.utime(newest, (now - 100, now - 100))

    report = manager.cleanup_directory("renders", ttl_seconds=999999, max_size_mb=1)

    assert not oldest.exists()
    assert middle.exists()
    assert newest.exists()
    assert report.reason_counts["size_limit"] >= 1


def test_delete_file_blocks_outside_allowed_directories(tmp_path: Path):
    manager = _make_manager(tmp_path / "cache_root")
    outside_file = tmp_path / "outside.png"
    outside_file.write_bytes(b"data")

    deleted = manager.delete_file(outside_file)

    assert deleted is False
    assert outside_file.exists()


@given(st.sampled_from([".py", ".json", ".yaml", ".env", ".db"]))
def test_cleanup_never_deletes_forbidden_suffixes(suffix: str):
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = _make_manager(Path(temp_dir) / "cache_root")
        target = manager.get_cache_dir("tmp") / f"unsafe{suffix}"
        target.write_text("unsafe", encoding="utf-8")
        _touch_old(target)

        manager.cleanup_directory("tmp", ttl_seconds=0, max_size_mb=0)

        assert target.exists()


def test_safe_cleaner_worker_run_once(tmp_path: Path):
    manager = _make_manager(tmp_path / "cache_root")
    stale_pdf = manager.get_cache_dir("pdf_temp") / "old.pdf"
    stale_pdf.write_bytes(b"pdf")
    _touch_old(stale_pdf)
    worker = SafeCleanerWorker(manager, interval_seconds=300)

    reports = worker.run_once()

    assert "pdf_temp" in reports
    assert not stale_pdf.exists()

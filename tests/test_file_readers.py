import pytest

from file_readers import (
    PathAccessError,
    UnsupportedFileTypeError,
    list_files_in_directory,
    read_file,
    resolve_safe_path,
)


def test_read_txt(sample_txt):
    text = read_file(sample_txt.name)
    assert "Project Phoenix" in text


def test_read_docx(sample_docx):
    text = read_file(sample_docx.name)
    assert "Quarterly Report" in text
    assert "Revenue grew by 20 percent" in text
    assert "Region | Sales" in text  # table row flattened


def test_read_xlsx(sample_xlsx):
    text = read_file(sample_xlsx.name)
    assert "Sheet: Sales" in text
    assert "North" in text
    assert "2000" in text


def test_read_file_not_found(sandbox):
    with pytest.raises(FileNotFoundError):
        read_file("does_not_exist.txt")


def test_unsupported_extension(sandbox):
    bad = sandbox / "image.png"
    bad.write_bytes(b"\x89PNG\r\n")
    with pytest.raises(UnsupportedFileTypeError):
        read_file("image.png")


def test_path_traversal_blocked(sandbox):
    with pytest.raises(PathAccessError):
        resolve_safe_path("../../etc/passwd")


def test_path_traversal_blocked_via_read(sandbox):
    with pytest.raises(PathAccessError):
        read_file("../outside.txt")


def test_list_files_recursive(nested_folder):
    files = list_files_in_directory(".", recursive=True)
    names = {f.name for f in files}
    assert "top.txt" in names
    assert "inner.txt" in names


def test_list_files_non_recursive(nested_folder):
    files = list_files_in_directory(".", recursive=False)
    names = {f.name for f in files}
    assert "top.txt" in names
    assert "inner.txt" not in names


def test_list_files_marks_unsupported(sandbox):
    (sandbox / "archive.zip").write_bytes(b"PK\x03\x04")
    files = list_files_in_directory(".")
    zip_entry = next(f for f in files if f.name == "archive.zip")
    assert zip_entry.is_supported is False


def test_list_files_missing_folder(sandbox):
    with pytest.raises(FileNotFoundError):
        list_files_in_directory("nope")

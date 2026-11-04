"""Small VFS contract experiment; only synthetic data and temporary storage.

Run with the fsspec version recorded in the article. This is a teaching example,
not a sandbox, an authorization service, or a production file implementation.
"""

import csv
import io
import json
import platform
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import fsspec


class TaskFiles:
    def __init__(self, bindings, writable):
        self.bindings = bindings
        self.writable = frozenset(writable)

    def read(self, logical_path):
        fs, backend_path = self.bindings[logical_path]
        return fs.cat(backend_path)

    def write(self, logical_path, data):
        if logical_path not in self.writable:
            raise PermissionError(logical_path)
        fs, backend_path = self.bindings[logical_path]
        fs.pipe(backend_path, data)


def build_report(files):
    rows = csv.DictReader(
        io.StringIO(files.read("/inputs/sales.csv").decode("utf-8"))
    )
    total = sum((Decimal(row["amount"]) for row in rows), Decimal("0"))
    files.write("/outputs/report.txt", f"total={total:.2f}\n".encode("utf-8"))


def rejected(action, error_type):
    try:
        action()
    except error_type:
        return True
    return False


def exercise(fs, prefix):
    source = f"{prefix}/sales.csv"
    result = f"{prefix}/report.txt"
    original = b"amount\n10.00\n20.00\n"
    fs.pipe(source, original)
    files = TaskFiles(
        {
            "/inputs/sales.csv": (fs, source),
            "/outputs/report.txt": (fs, result),
        },
        writable={"/outputs/report.txt"},
    )
    build_report(files)
    output = files.read("/outputs/report.txt").decode("utf-8").strip()
    input_write_rejected = rejected(
        lambda: files.write("/inputs/sales.csv", b"changed"), PermissionError
    )
    unbound_read_rejected = rejected(
        lambda: files.read("/other-task/secret.csv"), KeyError
    )
    assert fs.cat(source) == original

    # Negative control: a caller retaining the raw backend can bypass TaskFiles.
    fs.pipe(source, b"changed through the backend")
    raw_backend_bypasses_policy = (
        files.read("/inputs/sales.csv") == b"changed through the backend"
    )
    assert output == "total=30.00"
    assert input_write_rejected and unbound_read_rejected
    assert raw_backend_bypasses_policy
    return {
        "report": output,
        "input_write_rejected": input_write_rejected,
        "unbound_read_rejected": unbound_read_rejected,
        "raw_backend_bypasses_policy": raw_backend_bypasses_policy,
    }


def main():
    with TemporaryDirectory(prefix="vfs-contract-demo-") as directory:
        local = exercise(fsspec.filesystem("file"), str(Path(directory)))
    memory_fs = fsspec.filesystem("memory")
    memory_prefix = "/vfs-contract-demo-" + uuid4().hex
    try:
        memory = exercise(memory_fs, memory_prefix)
    finally:
        if memory_fs.exists(memory_prefix):
            memory_fs.rm(memory_prefix, recursive=True)
    assert local["report"] == memory["report"]
    print(
        json.dumps(
            {
                "python": platform.python_version(),
                "fsspec": fsspec.__version__,
                "same_tool_same_output": True,
                "local": local,
                "memory": memory,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

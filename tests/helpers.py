"""Tiện ích test: chạy headless, đọc JSONL, dựng fixture, so sánh có dung sai."""

import json
import math
import os
import shlex
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    return path


def frames(*fr):
    return {"frames": list(fr)}


def headless_cmd():
    """Lệnh headless khai trong game.contract.json — test chạy qua đây nên dùng được với MỌI ngôn ngữ."""
    with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
        return shlex.split(json.load(f)["headless_cmd"])


def run_headless(*args, cwd=ROOT):
    """Chạy `<headless_cmd> <args>`; trả (mã thoát, stderr)."""
    p = subprocess.run([*headless_cmd(), *args], cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stderr


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def snapshots(rows):
    return [r for r in rows if r["type"] == "snapshot"]


def events(rows, name=None):
    return [r for r in rows if r["type"] == "event" and (name is None or r["name"] == name)]


def close(a, b, tol=0.1):
    return abs(a - b) <= tol


def dist(p, q):
    return math.dist(p, q)


class Workdir:
    """Thư mục tạm tự dọn: with Workdir() as w: w.path('x.json')."""

    def __enter__(self):
        self._d = tempfile.TemporaryDirectory()
        return self

    def __exit__(self, *a):
        self._d.cleanup()

    def path(self, name):
        return os.path.join(self._d.name, name)


# --- v1.2: kho cá thể {id, kind, fresh} -------------------------------------------------------------
def item(kind, iid, fresh=100):
    return {"id": iid, "kind": kind, "fresh": fresh}


def items(*kinds, start=1, fresh=100):
    """items("ca_loc", "bong_sung") -> [{"id": "I1", "kind": "ca_loc", "fresh": 100}, {"id": "I2", ...}]"""
    return [item(k, f"I{start + i}", fresh) for i, k in enumerate(kinds)]


def stock_items(counts, start=1, fresh=100):
    """Chuyển fixture kho ĐẾM cũ {kind: n} (P1–P2) sang mảng cá thể v1.2, id I1… theo kind đã sắp."""
    ks = [k for k in sorted(counts) for _ in range(counts[k])]
    return items(*ks, start=start, fresh=fresh)


def as_items(v):
    """Fixture cũ -> v1.2: mảng chuỗi kind (giỏ) hoặc map đếm (kho) -> mảng cá thể; đã là cá thể thì giữ."""
    if isinstance(v, dict):
        return stock_items(v)
    if isinstance(v, list) and v and isinstance(v[0], str):
        return items(*v)
    return v


def kinds_of(arr):
    return [i["kind"] for i in arr]


def counts(arr):
    """Mảng cá thể -> map đếm theo kind (để so với kỳ vọng kiểu P1–P2)."""
    out = {}
    for i in arr:
        out[i["kind"]] = out.get(i["kind"], 0) + 1
    return {k: out[k] for k in sorted(out)}

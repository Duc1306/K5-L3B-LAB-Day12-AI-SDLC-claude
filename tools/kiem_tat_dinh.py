"""Kiểm tất định: chạy headless 2 lần cùng seed/đầu vào, so JSONL (và file kho) từng byte.

    python3 tools/kiem_tat_dinh.py --mode gather --seed 1 --ticks 600 [--inputs f.json] [--scenario s.json]
    python3 tools/kiem_tat_dinh.py --mode quan --seed 3 --ticks 10800 [--inventory kho.json]

Chạy qua `headless_cmd` trong game.contract.json (giống test hộp đen). Mã thoát: 0 trùng khớp,
1 lệch (in dòng khác đầu tiên), 2 headless báo lỗi. Không ghi gì vào repo (dùng thư mục tạm).
"""

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def headless_cmd():
    with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
        return shlex.split(json.load(f)["headless_cmd"])


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def first_diff(a, b):
    with open(a, "rb") as fa, open(b, "rb") as fb:
        la, lb = fa.read().splitlines(), fb.read().splitlines()
    for i, (x, y) in enumerate(zip(la, lb), 1):
        if x != y:
            return i, x.decode("utf-8"), y.decode("utf-8")
    return min(len(la), len(lb)) + 1, f"<{len(la)} dòng>", f"<{len(lb)} dòng>"


def main(argv=None):
    p = argparse.ArgumentParser(prog="kiem_tat_dinh")
    p.add_argument("--mode", required=True, choices=["gather", "quan", "day"])
    p.add_argument("--seed", required=True)
    p.add_argument("--ticks", required=True)
    for opt in ("--scenario", "--inputs", "--inventory", "--snapshot-every"):
        p.add_argument(opt)
    a = p.parse_args(argv)

    extra = []
    for opt, val in (("--scenario", a.scenario), ("--inputs", a.inputs), ("--inventory", a.inventory),
                     ("--snapshot-every", a.snapshot_every)):
        if val:
            extra += [opt, os.path.abspath(val) if opt != "--snapshot-every" else val]

    with tempfile.TemporaryDirectory() as d:
        outs = []
        for i in (1, 2):
            out, kho = os.path.join(d, f"o{i}.jsonl"), os.path.join(d, f"kho{i}.json")
            args = ["--mode", a.mode, "--seed", a.seed, "--ticks", a.ticks, "--out", out, *extra]
            if a.mode == "gather":
                args += ["--inventory-out", kho]
            r = subprocess.run([*headless_cmd(), *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            if r.returncode != 0:
                sys.stderr.write(f"lần {i}: headless thoát mã {r.returncode}\n{r.stderr}")
                return 2
            outs.append((out, kho))

        ok = True
        (o1, k1), (o2, k2) = outs
        h1, h2 = sha(o1), sha(o2)
        print(f"JSONL  lần 1 {h1}\nJSONL  lần 2 {h2}")
        if h1 != h2:
            ok = False
            n, x, y = first_diff(o1, o2)
            print(f"LỆCH ở dòng {n}:\n  lần 1: {x}\n  lần 2: {y}")
        e1, e2 = os.path.exists(k1), os.path.exists(k2)
        if e1 or e2:
            if e1 != e2 or sha(k1) != sha(k2):
                ok = False
                print("LỆCH file kho")
            else:
                print(f"Kho    hai lần {sha(k1)}")
        elif a.mode == "gather":
            print("Kho    không ghi (gather chưa kết thúc trong --ticks)")
        print("TẤT ĐỊNH: OK" if ok else "TẤT ĐỊNH: LỆCH")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

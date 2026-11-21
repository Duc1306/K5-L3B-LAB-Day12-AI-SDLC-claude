"""Sinh bằng chứng Phase 3 (TICKET-03, contract v1.2) vào docs/proof/phase-3/. Chạy hộp đen qua headless_cmd.

    python3 tools/proof_phase3.py

Ghi: các file vào/ra (json/jsonl) và `checks.md` tóm tắt kết quả (đạt/không đạt) của từng kiểm tra.
"""

import hashlib
import json
import os
import shlex
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "proof", "phase-3")
CMD = shlex.split(json.load(open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8"))["headless_cmd"])
LOG = []


def p(name):
    return os.path.join(OUT, name)


def rel(name):
    return f"docs/proof/phase-3/{name}"


def write(name, obj):
    with open(p(name), "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False)
        f.write("\n")
    return p(name)


def run(*args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    t0 = time.perf_counter()
    r = subprocess.run([*CMD, *args], cwd=ROOT, capture_output=True, text=True, env=env)
    return r.returncode, r.stderr.strip(), time.perf_counter() - t0


def rows(name):
    with open(p(name), encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def check(title, ok, detail):
    LOG.append((title, ok, detail))
    print(("ĐẠT  " if ok else "LỖI  ") + title)


def shell(args):
    return " ".join(["python3 -m chonoi.headless", *[a.replace(ROOT + os.sep, "").replace("\\", "/") for a in args]])


def main():
    os.makedirs(OUT, exist_ok=True)
    # 1. Ví dụ ngưỡng trong đề
    sc = write("threshold-sc.json", {"gather": {"hold": [{"id": "I1", "kind": "ca_linh", "fresh": 30}],
                                                 "random_fish": False, "monsters": []}})
    args = ["--mode", "gather", "--seed", "1", "--ticks", "1", "--scenario", sc, "--out", p("threshold.jsonl")]
    code, err, _ = run(*args)
    ev = [r for r in rows("threshold.jsonl") if r["type"] == "event"]
    want = {"type": "event", "tick": 1, "phase": "gather", "name": "spoiled",
            "data": {"item_id": "I1", "kind": "ca_linh", "location": "hold"}}
    check("Ngưỡng 30: spoiled ở tick 1 đúng nguyên văn đề", code == 0 and ev == [want],
          f"`{shell(args)}` → `{json.dumps(ev[0], ensure_ascii=False) if ev else err}`")

    # 2. Smoke bàn giao file theo đề
    sc = write("handoff-sc.json", {"gather": {"hold": [{"id": "I1", "kind": "ca_linh", "fresh": 100}],
                                               "random_fish": False, "monsters": []}})
    inp = write("handoff-inputs.json", {"frames": [{"tick": 0, "interact": True}]})
    kho = p("handoff-kho.json")
    if os.path.exists(kho):
        os.remove(kho)
    a1 = ["--mode", "gather", "--seed", "1", "--ticks", "10", "--scenario", sc, "--inputs", inp,
          "--inventory-out", kho, "--out", p("handoff-gather.jsonl")]
    c1, e1, _ = run(*a1)
    a2 = ["--mode", "quan", "--seed", "1", "--ticks", "0", "--inventory", kho, "--out", p("handoff-quan.jsonl")]
    c2, e2, _ = run(*a2)
    saved = json.load(open(kho, encoding="utf-8"))
    stock = rows("handoff-quan.jsonl")[0]["stock"]
    same = [(i["id"], i["kind"]) for i in stock] == [(i["id"], i["kind"]) for i in saved["items"]] and \
        all(abs(a["fresh"] - b["fresh"]) <= 0.01 for a, b in zip(stock, saved["items"]))
    check("Smoke bàn giao file: quán nhận đúng id, kind, độ tươi sau lần hao ở bước gather",
          c1 == 0 and c2 == 0 and same and saved["items"][0]["fresh"] == (24000 - 2) / 240,
          f"`{shell(a1)}` rồi `{shell(a2)}`. File kho: `{json.dumps(saved)}`; snapshot quán tick 0: "
          f"`{json.dumps(stock)}`")

    # 3. Ngưỡng giữ nhánh qua file (30.00833 -> 30 sau gather -> ươn ở quán bước 1)
    sc = write("edge-sc.json", {"gather": {"hold": [{"id": "I1", "kind": "ca_loc", "fresh": 7202 / 240}],
                                            "random_fish": False, "monsters": []}})
    kho2 = p("edge-kho.json")
    if os.path.exists(kho2):
        os.remove(kho2)
    a1 = ["--mode", "gather", "--seed", "1", "--ticks", "5", "--scenario", sc, "--inputs", inp,
          "--inventory-out", kho2, "--out", p("edge-gather.jsonl")]
    run(*a1)
    qsc = write("edge-quan-sc.json", {"quan": {"random_customers": False}})
    a2 = ["--mode", "quan", "--seed", "1", "--ticks", "1", "--inventory", kho2, "--scenario", qsc,
          "--out", p("edge-quan.jsonl")]
    run(*a2)
    saved2 = json.load(open(kho2, encoding="utf-8"))
    sp = [r for r in rows("edge-quan.jsonl") if r["type"] == "event" and r["name"] == "spoiled"]
    check("Nhánh ngưỡng giữ nguyên qua file: 30 đúng trong kho, ươn ở bước quán đầu (location stock)",
          saved2["items"][0]["fresh"] == 30 and [(r["tick"], r["data"]["location"]) for r in sp] == [(1, "stock")],
          f"Kho sau gather: `{json.dumps(saved2)}`; event quán: `{json.dumps(sp, ensure_ascii=False)}`")

    # 4. Kho đếm / sai schema -> mã 2, không ghi đầu ra
    bad = {"kho-dem.json": {"items": {"ca_loc": 1}},
           "kho-id-trung.json": {"items": [{"id": "I1", "kind": "ca_loc", "fresh": 50},
                                           {"id": "I1", "kind": "ca_loc", "fresh": 60}]},
           "kho-fresh-ngoai-mien.json": {"items": [{"id": "I1", "kind": "ca_loc", "fresh": 120}]},
           "kho-kind-la.json": {"items": [{"id": "I1", "kind": "ca_rong", "fresh": 50}]}}
    res = []
    for name, obj in bad.items():
        out = p("bad.jsonl")
        if os.path.exists(out):
            os.remove(out)
        c, e, _ = run("--mode", "quan", "--seed", "1", "--ticks", "0", "--inventory", write(name, obj), "--out", out)
        res.append((name, c, os.path.exists(out), e))
    check("Contract v1.2: file kho đếm / sai schema → mã 2, không ghi đầu ra",
          all(c == 2 and not ex for _, c, ex, _ in res),
          "; ".join(f"`{n}` → mã {c} ({e.splitlines()[-1] if e else ''})" for n, c, _, e in res))

    # 5. day 2 Ngày: bàn giao cùng tick, id tăng xuyên Ngày, thời gian
    dsc = write("day-sc.json", {"gather": {"hold": [{"id": "I1", "kind": "ca_loc", "fresh": 100},
                                                     {"id": "I2", "kind": "bong_sung", "fresh": 100},
                                                     {"id": "I3", "kind": "bong_sung", "fresh": 100}],
                                            "random_fish": False},
                                 "quan": {"time_left_ticks": 600}})
    a = ["--mode", "day", "--days", "2", "--seed", "1", "--ticks", "50000", "--scenario", dsc, "--inputs", inp,
         "--snapshot-every", "600", "--out", p("day2.jsonl")]
    c, e, dt = run(*a)
    rs = rows("day2.jsonl")
    ge = [r for r in rs if r["type"] == "event" and r["name"] == "gather_end"]
    q0 = [r for r in rs if r["type"] == "snapshot" and r["phase"] == "quan" and r["phase_tick"] == 0]
    d2 = [r for r in rs if r["type"] == "snapshot" and r.get("day") == 2 and r["phase"] == "gather"]
    ok = c == 0 and q0[0]["tick"] == ge[0]["tick"] and q0[0]["stock"] == ge[0]["data"]["inventory"]["items"] and \
        [i["id"] for i in d2[0]["hold"]] == ["I4", "I5", "I6"] and rs[-1]["reason"] == "days_complete"
    check("`day`: bàn giao cùng tick không hao thêm; Ngày 2 cấp id mới I4–I6 theo mẫu",
          ok, f"`{shell(a)}` ({dt:.2f} s) → gather_end tick {ge[0]['tick']}, snapshot quán phase_tick 0 cùng tick, "
              f"kho `{[i['id'] for i in q0[0]['stock']]}`; Ngày 2 giỏ `{[i['id'] for i in d2[0]['hold']]}`; "
              f"end `{rs[-1]['reason']}`, days_completed {rs[-1]['days_completed']}")

    a = ["--mode", "day", "--days", "1", "--seed", "1", "--ticks", "22200", "--snapshot-every", "600",
         "--out", p("day1.jsonl")]
    c, e, dt = run(*a)
    check("Headless một Ngày không pause (22200 tick) ≤ 20 s", c == 0 and dt <= 20, f"`{shell(a)}` → {dt:.2f} s")

    # 6. Tất định
    hs = []
    for i in (1, 2):
        a = ["--mode", "day", "--days", "2", "--seed", "7", "--ticks", "30000", "--scenario", dsc, "--inputs", inp,
             "--snapshot-every", "600", "--out", p(f"det-{i}.jsonl")]
        run(*a)
        hs.append(hashlib.sha256(open(p(f"det-{i}.jsonl"), "rb").read()).hexdigest())
    check("Tất định: 2 lần `day --days 2` cùng seed giống từng byte", hs[0] == hs[1], f"sha256 `{hs[0][:16]}…` × 2")

    with open(p("checks.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("# Kiểm chứng chạy thật Phase 3 (contract v1.2)\n\n")
        f.write("Sinh bằng `python3 tools/proof_phase3.py`. File vào/ra nằm cùng thư mục.\n\n")
        f.write("| # | Kiểm tra | Kết quả | Chi tiết |\n|---|---|---|---|\n")
        for i, (t, ok, d) in enumerate(LOG, 1):
            f.write(f"| {i} | {t} | {'Đạt' if ok else '**Không đạt**'} | {d.replace('|', '¦')} |\n")
    return 0 if all(ok for _, ok, _ in LOG) else 1


if __name__ == "__main__":
    sys.exit(main())

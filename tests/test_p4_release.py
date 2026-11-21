"""Test Phase 4 (TICKET-04, Test Contract v1.3): manifest, soak headless, phép tính bench, cảnh báo + tương phản cao.

Soak chạy hộp đen qua `soak_cmd` trong game.contract.json. Bench thật cần trình duyệt nên chỉ kiểm phép tính
(`chonoi.bench.compute`) và tham số sai; số đo thật lưu ở docs/proof/phase-4/bench.json.
"""

import json
import math
import os
import shlex
import subprocess
import unittest

from chonoi.bench import compute
from chonoi.contract import load_contract
from chonoi.sim.day import DaySim
from chonoi.sim.plan import plan_for_day

from helpers import ROOT, Workdir, run_headless

C = load_contract()
GAMEPLAY = ("days", "days_completed", "crashes", "results")


def run_cmd(key, *args):
    p = subprocess.run([*shlex.split(C[key]), *args], cwd=ROOT, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return p.returncode, p.stderr


class Manifest(unittest.TestCase):
    def test_v13_khai_bench_va_soak(self):
        self.assertEqual(C["contract_version"], "1.3")
        self.assertEqual(C["bench_cmd"], "python3 -m chonoi.bench")
        self.assertEqual(C["soak_cmd"], "python3 -m chonoi.soak")
        for key in ("bench_cmd", "soak_cmd"):
            code, err = run_cmd(key, "--help")
            self.assertEqual(code, 0, err)

    def test_gameplay_va_kho_van_theo_v12(self):
        self.assertEqual(C["tuning"]["freshness"]["spoiled_below"], 30)
        with Workdir() as w:   # headless vẫn giới hạn --days 1..5 của v1.1
            self.assertEqual(run_headless("--mode", "day", "--days", "6", "--seed", "1", "--ticks", "0",
                                          "--out", w.path("o.jsonl"))[0], 2)


class Soak(unittest.TestCase):
    def soak(self, w, name, days, seed=7):
        out = w.path(name)
        code, err = run_cmd("soak_cmd", "--seed", str(seed), "--days", str(days), "--out", out)
        with open(out, encoding="utf-8") as f:
            return code, err, json.load(f)

    def test_soak_cau_truc_va_tat_dinh(self):
        with Workdir() as w:
            code, err, a = self.soak(w, "a.json", 2)
            self.assertEqual(code, 0, err)
            self.assertEqual(set(a), {"days", "days_completed", "crashes", "results", "duration_s"})
            self.assertEqual((a["days"], a["days_completed"], a["crashes"]), (2, 2, 0))
            self.assertEqual([r["day"] for r in a["results"]], [1, 2])
            mult = C["tuning"]["score"]["reputation_multiplier"]
            for r in a["results"]:
                self.assertEqual(set(r), {"day", "earned", "reputation", "score"})
                self.assertEqual(r["score"], r["earned"] + mult * math.floor(r["reputation"]))
            self.assertGreater(a["results"][-1]["earned"], 0, "bot phải thật sự nấu và bán được món")
            _, _, b = self.soak(w, "b.json", 2)
            self.assertEqual({k: a[k] for k in GAMEPLAY}, {k: b[k] for k in GAMEPLAY}, "lặp lại đúng, bỏ duration_s")

    def test_tham_so_sai_ma_2(self):
        with Workdir() as w:
            self.assertEqual(run_cmd("soak_cmd", "--seed", "1", "--days", "0", "--out", w.path("x.json"))[0], 2)
            self.assertEqual(run_cmd("soak_cmd", "--seed", "x", "--days", "1", "--out", w.path("x.json"))[0], 2)

    def test_ke_hoach_D1_D5_lap_o_ngay_6_10(self):
        t = C["tuning"]
        sim = DaySim(t, {}, 1, days=10)
        for n in range(1, 11):
            self.assertEqual(sim._plan_for(n), plan_for_day(t, (n - 1) % 5 + 1), n)


class BenchMath(unittest.TestCase):
    def test_cong_thuc_5_truong(self):
        ts = [1000.0, 1016.0, 1032.0, 1048.0, 1100.0]          # 4 khung: 16, 16, 16, 52 ms
        out = compute(ts, first_epoch_ms=5000.0, launch_ms=2600.0)
        self.assertEqual(set(out), {"avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms"})
        self.assertEqual(out["frames"], 4)
        self.assertAlmostEqual(out["measured_s"], 0.1, places=6)
        self.assertAlmostEqual(out["avg_fps"], 40.0, places=2)
        self.assertAlmostEqual(out["p1_low_fps"], round(1 / 0.052, 2), places=2)   # max(1, ceil(0.04)) = 1 khung chậm nhất
        self.assertEqual(out["load_ms"], 2400)

    def test_p1_low_lay_1_phan_tram_cham_nhat(self):
        ts = [i * 10.0 for i in range(201)]                     # 200 khung 10 ms ...
        ts[100:] = [t + 30.0 for t in ts[100:]]                 # ... một khung 40 ms
        ts[150:] = [t + 10.0 for t in ts[150:]]                 # ... một khung 20 ms
        out = compute(ts, first_epoch_ms=0.0, launch_ms=0.0)
        self.assertEqual(out["frames"], 200)
        self.assertAlmostEqual(out["p1_low_fps"], round(1 / 0.030, 2), places=2)   # ceil(2) = 2 khung: (40 + 20)/2 ms

    def test_tham_so_sai(self):
        with Workdir() as w:
            self.assertEqual(run_cmd("bench_cmd", "--seed", "42", "--duration", "0", "--out", w.path("b.json"))[0], 2)


class WarningsUI(unittest.TestCase):
    def test_trang_co_3_canh_bao_tuong_phan_cao_va_bench(self):
        with open(os.path.join(ROOT, "chonoi", "web", "index.html"), encoding="utf-8") as f:
            page = f.read()
        for s in ("Thủy quái gần!", "Oxy sắp hết!", "Khách sắp giận!", "tuong_phan", "toggleHC", "benchCollector", "/bench"):
            self.assertIn(s, page)


if __name__ == "__main__":
    unittest.main()

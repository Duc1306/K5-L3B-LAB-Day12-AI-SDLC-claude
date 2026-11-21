"""Chế độ `day`, Shop và pause (TICKET-02 mục 2, Test Contract v1.1 mục 4.1–4.5). Chạy hộp đen qua headless_cmd."""

import json
import unittest

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json

DOCK_SC = {"day": {}, "gather": {"hold": ["ca_loc", "bong_sung", "bong_sung"], "random_fish": False},
           "quan": {"time_left_ticks": 20}}


def day_run(w, *, days=1, ticks=30000, scenario=None, inputs=None, every=10, seed=1, name="o"):
    out = w.path(name + ".jsonl")
    args = ["--mode", "day", "--seed", str(seed), "--days", str(days), "--ticks", str(ticks), "--out", out,
            "--snapshot-every", str(every)]
    if scenario is not None:
        args += ["--scenario", write_json(w.path(name + "-sc.json"), scenario)]
    if inputs is not None:
        args += ["--inputs", write_json(w.path(name + "-in.json"), inputs)]
    code, err = run_headless(*args)
    return code, err, (read_jsonl(out) if code == 0 else None)


def snap_at(rows, tick):
    return [s for s in snapshots(rows) if s["tick"] == tick][-1]


def ev_names(rows, tick):
    return [e["name"] for e in events(rows) if e["tick"] == tick]


# Ngày ngắn: cập bến ở tick 0, quán 20 tick, rồi các lệnh Shop
def short_day_frames(*shop_frames):
    return frames({"tick": 0, "interact": True}, {"tick": 1, "interact": False}, *shop_frames)


class DayFlowTest(unittest.TestCase):
    def test_mot_ngay_khong_pause_dung_22200_tick_va_thu_tu_su_kien(self):
        with Workdir() as w:
            code, err, rows = day_run(w)
            self.assertEqual(code, 0, err)
            self.assertEqual([e["name"] for e in events(rows)[:3]], ["day_start", "day_plan", "phase_start"])
            self.assertTrue(all(e["tick"] == 0 and e["day"] == 1 and e["phase"] == "gather" for e in events(rows)[:3]))
            plan = events(rows, "day_plan")[0]["data"]
            self.assertEqual(plan, {"dishes": {"ca_loc_nuong_trui": 3, "goi_bong_sung": 3}, "ingredients": {"bong_sung": 6, "ca_loc": 3}})
            end = rows[-1]
            self.assertEqual((end["ticks"], end["reason"], end["days_completed"], end["mode"]), (22200, "days_complete", 1, "day"))
            self.assertEqual(events(rows, "shop_end")[0]["data"], {"reason": "time"})
            s0 = snapshots(rows)[0]
            for k in ("day", "day_plan", "upgrades", "active_upgrades"):
                self.assertIn(k, s0)

    def test_doi_pha_cung_tick_kho_ban_giao_va_snapshot_pha_moi(self):
        with Workdir() as w:
            code, err, rows = day_run(w, scenario=DOCK_SC, inputs=short_day_frames(), ticks=30, every=1000)
            self.assertEqual(code, 0, err)
            self.assertEqual(ev_names(rows, 1), ["gather_end", "phase_start"])
            ge, ps = events(rows, "gather_end")[0], events(rows, "phase_start")[1]
            self.assertEqual((ge["phase"], ps["phase"]), ("gather", "quan"))   # event kết thúc mang pha cũ
            s = snap_at(rows, 1)
            self.assertEqual((s["phase"], s["phase_tick"]), ("quan", 0))
            self.assertEqual(s["stock"], ge["data"]["inventory"]["items"])
            self.assertEqual(ev_names(rows, 21), ["quan_end", "phase_start"])
            self.assertEqual(snap_at(rows, 21)["phase"], "shop")

    def test_ngat_van_mo_quan_voi_kho_rong(self):
        sc = {"gather": {"player": {"pos": [20, 10], "oxygen_ticks": 0, "hp": 1, "zero_oxy_ticks": 59},
                         "hold": ["ca_loc"], "random_fish": False}}
        with Workdir() as w:
            code, err, rows = day_run(w, scenario=sc, ticks=5, every=1000)
            self.assertEqual(code, 0, err)
            self.assertEqual(events(rows, "gather_end")[0]["data"]["reason"], "fainted")
            self.assertEqual(snap_at(rows, 1)["phase"], "quan")
            self.assertEqual(snap_at(rows, 1)["stock"], {})

    def test_quan_chi_ban_mon_trong_ke_hoach(self):
        # Ngày 1 kế hoạch: cá lóc nướng trui + gỏi bông súng. Có đủ đồ nấu lẩu nhưng lẩu ngoài kế hoạch -> no_dish.
        sc = {"gather": {"hold": ["ca_linh", "ca_linh", "ca_linh", "bong_dien_dien"], "random_fish": False}}
        with Workdir() as w:
            code, err, rows = day_run(w, scenario=sc, inputs=short_day_frames(), ticks=200, every=1000)
            self.assertEqual(code, 0, err)
            self.assertEqual(len(events(rows, "no_dish")), 1)
            self.assertEqual(events(rows, "customer_arrived"), [])

    def test_ghi_de_ke_hoach_ngay_bang_scenario(self):
        sc = {"day": {"day_plan": [{"day": 1, "dishes": {"lau_ca_linh_dien_dien": 1}}]},
              "gather": {"hold": ["ca_linh", "ca_linh", "ca_linh", "bong_dien_dien"], "random_fish": False}}
        with Workdir() as w:
            code, err, rows = day_run(w, scenario=sc, inputs=short_day_frames(), ticks=200, every=1000)
            self.assertEqual(code, 0, err)
            self.assertEqual(events(rows, "day_plan")[0]["data"]["ingredients"], {"bong_dien_dien": 1, "ca_linh": 3})
            self.assertEqual(events(rows, "customer_arrived")[0]["data"]["dish_id"], "lau_ca_linh_dien_dien")

    def test_ca_sau_m2_chi_tu_ngay_3(self):
        sc = {"gather": {"random_fish": False}, "quan": {"time_left_ticks": 20}}
        fr = frames({"tick": 0, "interact": True}, {"tick": 1, "interact": False},
                    {"tick": 21, "shop_done": True}, {"tick": 22, "shop_done": False, "interact": True},
                    {"tick": 23, "interact": False}, {"tick": 43, "shop_done": True},
                    {"tick": 44, "shop_done": False})
        with Workdir() as w:
            code, err, rows = day_run(w, days=3, scenario=sc, inputs=fr, ticks=46, every=1000)
            self.assertEqual(code, 0, err)
            starts = {e["day"]: e["tick"] for e in events(rows, "day_start")}
            self.assertEqual(starts, {1: 0, 2: 22, 3: 44})
            ids = lambda t: [m["id"] for m in snap_at(rows, t)["monsters"]]
            self.assertEqual((ids(0), ids(22), ids(44)), (["M1"], ["M1"], ["M1", "M2"]))


class ShopTest(unittest.TestCase):
    def test_mua_tru_money_giu_earned_va_ap_dung_tu_ngay_ke(self):
        sc = dict(DOCK_SC, day={"money": 650, "earned": 650})
        fr = short_day_frames({"tick": 21, "buy": "oxygen"}, {"tick": 22, "buy": "hp"}, {"tick": 23, "shop_done": True})
        with Workdir() as w:
            code, err, rows = day_run(w, days=2, scenario=sc, inputs=fr, ticks=26, every=1)
            self.assertEqual(code, 0, err)
            b = events(rows, "bought")
            self.assertEqual([e["data"] for e in b], [{"upgrade": "oxygen", "level": 1, "price": 200, "money": 450},
                                                     {"upgrade": "hp", "level": 1, "price": 250, "money": 200}])
            shop = snap_at(rows, 23)
            self.assertEqual((shop["upgrades"], shop["active_upgrades"]), ({"hp": 1, "oxygen": 1}, {}))  # hiện ngay, chưa áp dụng
            d2 = snap_at(rows, 24)
            self.assertEqual((d2["day"], d2["phase"], d2["active_upgrades"]), (2, "gather", {"hp": 1, "oxygen": 1}))
            self.assertEqual((d2["player"]["oxygen_max_ticks"], d2["player"]["hp_max"], d2["player"]["hp"]), (2700, 4, 4))
            self.assertEqual((d2["money"], d2["earned"], d2["score"]), (200, 650, 650 + 300))

    def test_buy_failed_funds_max_level_unknown_va_dung_gia_van_mua(self):
        sc = dict(DOCK_SC, day={"money": 200, "earned": 200, "upgrades": {"hp": 2}})
        fr = short_day_frames({"tick": 21, "buy": "hp"}, {"tick": 22, "buy": "weapon"},
                              {"tick": 23, "buy": "oxygen"}, {"tick": 24, "buy": "oxygen"})
        with Workdir() as w:
            code, err, rows = day_run(w, scenario=sc, inputs=fr, ticks=26, every=1000)
            self.assertEqual(code, 0, err)
            got = [(e["name"], e["data"]) for e in events(rows) if e["name"] in ("bought", "buy_failed")]
            self.assertEqual(got, [("buy_failed", {"action": "hp", "reason": "max_level"}),
                                   ("buy_failed", {"action": "weapon", "reason": "unknown"}),
                                   ("bought", {"upgrade": "oxygen", "level": 1, "price": 200, "money": 0}),
                                   ("buy_failed", {"action": "oxygen", "reason": "funds"})])

    def test_buy_truoc_shop_done_cung_buoc_va_buy_ngoai_shop_bo_qua(self):
        sc = dict(DOCK_SC, day={"money": 300, "earned": 300})
        fr = frames({"tick": 0, "interact": True, "buy": "oxygen"}, {"tick": 1, "interact": False},
                    {"tick": 21, "buy": "oxygen", "shop_done": True})
        with Workdir() as w:
            code, err, rows = day_run(w, scenario=sc, inputs=fr, ticks=30, every=1000)
            self.assertEqual(code, 0, err)
            self.assertEqual(ev_names(rows, 22), ["bought", "shop_end"])
            self.assertEqual(len(events(rows, "bought")), 1)          # buy ở gather bị bỏ qua
            self.assertEqual((rows[-1]["reason"], rows[-1]["days_completed"]), ("days_complete", 1))


class PauseTest(unittest.TestCase):
    def test_pause_dung_sim_tick_bo_qua_hanh_dong_va_resume_chay_ngay(self):
        fr = frames({"tick": 0, "pause": True}, {"tick": 1, "pause": False, "interact": True},
                    {"tick": 2, "interact": False}, {"tick": 5, "pause": True, "interact": True})
        with Workdir() as w:
            out = w.path("g.jsonl")
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "8", "--snapshot-every", "1",
                                     "--inputs", write_json(w.path("i.json"), fr), "--out", out)
            self.assertEqual(code, 0, err)
            rows = read_jsonl(out)
            self.assertEqual([(e["tick"], e["name"]) for e in events(rows)][:2], [(1, "paused"), (6, "resumed")])
            s3 = snap_at(rows, 3)
            self.assertEqual((s3["state"], s3["sim_tick"], s3["phase_tick"]), ("paused", 0, 0))
            self.assertEqual(events(rows, "gather_end")[0]["tick"], 6)  # E trong pause bị bỏ; E cùng bước resume có hiệu lực
            self.assertEqual((rows[-1]["ticks"], rows[-1]["sim_tick"]), (6, 1))

    def test_pause_trong_shop_dung_dong_ho_shop(self):
        fr = short_day_frames({"tick": 21, "pause": True}, {"tick": 22, "pause": False})
        with Workdir() as w:
            code, err, rows = day_run(w, scenario=DOCK_SC, inputs=fr, ticks=200, every=1000)
            self.assertEqual(code, 0, err)
            snap = snapshots(rows)[-1]
            self.assertEqual((snap["phase"], snap["state"], snap["time_left_ticks"]), ("shop", "paused", 600))


class DayCliAndScenarioTest(unittest.TestCase):
    def test_ma_2_cho_co_va_scenario_sai(self):
        bad = [
            ({"quan": {"stock": {"ca_loc": 1}}}, "quan.stock bị cấm trong day"),
            ({"quan": {"reputation": 4}}, "quan.reputation bị cấm trong day"),
            ({"day": {"money": 100, "earned": 50}}, "money > earned"),
            ({"day": {"money": 100}}, "có tiền đầu kỳ mà thiếu earned"),
            ({"day": {"upgrades": {"oxygen": 3}}}, "cấp vượt tối đa"),
            ({"day": {"upgrades": {"weapon": 1}}}, "mở rộng chưa bật"),
            ({"day": {"day_plan": [{"day": 1, "dishes": {"mon_la": 1}}]}}, "món ngoài thực đơn"),
            ({"day": {"day_plan": [{"day": 1, "dishes": {"goi_bong_sung": 1}, "ingredients": {"bong_sung": 3}}]}}, "ingredients sai"),
            ({"river": {}}, "khối lạ"),
        ]
        with Workdir() as w:
            out = w.path("o.jsonl")
            for i, (sc, why) in enumerate(bad):
                p = write_json(w.path(f"s{i}.json"), sc)
                self.assertEqual(run_headless("--mode", "day", "--seed", "1", "--ticks", "0", "--scenario", p, "--out", out)[0], 2, why)
            for args, why in ((["--days", "6"], "--days ngoài 1..5"), (["--days", "0"], "--days = 0")):
                self.assertEqual(run_headless("--mode", "day", "--seed", "1", "--ticks", "0", "--out", out, *args)[0], 2, why)
            self.assertEqual(run_headless("--mode", "gather", "--seed", "1", "--ticks", "0", "--days", "1", "--out", out)[0], 2)
            kho = write_json(w.path("k.json"), {"items": {}})
            self.assertEqual(run_headless("--mode", "day", "--seed", "1", "--ticks", "0", "--inventory", kho, "--out", out)[0], 2)

    def test_khach_mau_goi_mon_ngoai_ke_hoach_la_ma_2_luc_mo_quan(self):
        sc = {"gather": {"hold": ["ca_loc"], "random_fish": False},
              "quan": {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_keo_nuong"}]}}
        with Workdir() as w:
            code, _, _ = day_run(w, scenario=sc, inputs=short_day_frames(), ticks=10)
            self.assertEqual(code, 2)

    def test_tat_dinh_tung_byte(self):
        sc = dict(DOCK_SC, day={"money": 650, "earned": 650})
        fr = short_day_frames({"tick": 21, "buy": "oxygen"}, {"tick": 22, "shop_done": True})
        with Workdir() as w:
            a = day_run(w, days=2, scenario=sc, inputs=fr, ticks=2000, seed=7, name="a")
            b = day_run(w, days=2, scenario=sc, inputs=fr, ticks=2000, seed=7, name="b")
            self.assertEqual(a[0], 0, a[1])
            with open(w.path("a.jsonl"), "rb") as fa, open(w.path("b.jsonl"), "rb") as fb:
                self.assertEqual(fa.read(), fb.read())


if __name__ == "__main__":
    unittest.main()

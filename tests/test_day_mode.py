"""Chế độ `day`, Shop và pause (TICKET-02 mục 2, Test Contract v1.1 mục 4.1–4.5). Hộp đen qua headless_cmd."""

import json
import unittest

from helpers import Workdir, as_items, counts, events, frames, read_jsonl, run_headless, snapshots, write_json

with open("game.contract.json", encoding="utf-8") as _f:
    T = json.load(_f)["tuning"]
G_TICKS = int(T["gather"]["duration_s"] * 60)
Q_TICKS = int(T["quan"]["duration_s"] * 60)
S_TICKS = int(T["shop"]["max_ticks"])
DAY_TICKS = G_TICKS + Q_TICKS + S_TICKS  # 22.200: một Ngày không pause

# Mở Ngày đã có tiền và hàng: tương tác ở bến (tick 0) đóng ca sáng ngay (ví dụ v1.1 mục 4.3).
RICH = {"day": {"money": 200, "earned": 200},
        "gather": {"hold": as_items(["ca_loc", "bong_sung", "bong_sung"]), "random_fish": False}}  # v1.2: cá thể
DOCK = {"tick": 0, "interact": True}


def run_day(w, *extra, scenario=None, inputs=None, ticks=None, days=1, every=None, name="d"):
    args = ["--mode", "day", "--seed", "1", "--days", str(days), "--ticks", str(ticks or DAY_TICKS * days + 5),
            "--out", w.path(f"{name}.jsonl")]
    if scenario is not None:
        args += ["--scenario", write_json(w.path(f"{name}-sc.json"), scenario)]
    if inputs is not None:
        args += ["--inputs", write_json(w.path(f"{name}-in.json"), frames(*inputs))]
    if every:
        args += ["--snapshot-every", str(every)]
    code, err = run_headless(*args, *extra)
    return code, err, (read_jsonl(w.path(f"{name}.jsonl")) if code == 0 else None)


def ev(rows, name):
    return events(rows, name)


class DayLoop(unittest.TestCase):
    def test_mot_ngay_khong_input_du_ba_pha_va_end(self):
        with Workdir() as w:
            code, err, rows = run_day(w)
            self.assertEqual(code, 0, err)
            head = [r for r in rows if r["type"] == "event" and r["tick"] == 0]
            self.assertEqual([r["name"] for r in head], ["day_start", "day_plan", "phase_start"])
            self.assertTrue(all(r["day"] == 1 and r["phase"] == "gather" for r in head))
            self.assertEqual(head[1]["data"], {"dishes": {"ca_loc_nuong_trui": 3, "goi_bong_sung": 3},
                                               "ingredients": {"ca_loc": 3, "bong_sung": 6}})
            ge, = ev(rows, "gather_end")
            self.assertEqual((ge["tick"], ge["phase"], ge["data"]["reason"]), (G_TICKS, "gather", "time"))
            starts = [(r["tick"], r["phase"]) for r in ev(rows, "phase_start")]
            self.assertEqual(starts, [(0, "gather"), (G_TICKS, "quan"), (G_TICKS + Q_TICKS, "shop")])
            qe, = ev(rows, "quan_end")
            self.assertEqual((qe["tick"], qe["phase"]), (G_TICKS + Q_TICKS, "quan"))
            se, = ev(rows, "shop_end")
            self.assertEqual((se["tick"], se["phase"], se["data"]), (DAY_TICKS, "shop", {"reason": "time"}))
            end = rows[-1]
            self.assertEqual(end["type"], "end")
            self.assertEqual((end["mode"], end["state"], end["reason"], end["ticks"], end["sim_tick"],
                              end["days_completed"]), ("day", "finished", "days_complete", DAY_TICKS, DAY_TICKS, 1))
            self.assertEqual(end["score"], end["earned"] + 100 * int(end["reputation"]))
            self.assertTrue(all("day" in r for r in rows if r["type"] == "event"))

    def test_snapshot_moi_pha_co_truong_day_va_doi_pha_phase_tick_0(self):
        with Workdir() as w:
            code, err, rows = run_day(w, every=600)
            self.assertEqual(code, 0, err)
            snaps = snapshots(rows)
            for s in snaps:
                for k in ("day", "day_plan", "upgrades", "active_upgrades"):
                    self.assertIn(k, s)
                self.assertEqual(s["mode"], "day")
            by_tick = {s["tick"]: s for s in snaps}
            self.assertEqual((by_tick[G_TICKS]["phase"], by_tick[G_TICKS]["phase_tick"]), ("quan", 0))
            shop = by_tick[G_TICKS + Q_TICKS]
            self.assertEqual((shop["phase"], shop["phase_tick"], shop["time_left_ticks"]), ("shop", 0, S_TICKS))
            self.assertIn("stock", shop)
            self.assertEqual({s["phase"] for s in snaps}, {"gather", "quan", "shop"})

    def test_cap_ben_mo_quan_cung_tick_voi_kho_ban_giao_va_tien_mang_sang(self):
        with Workdir() as w:
            code, err, rows = run_day(w, scenario=RICH, inputs=[DOCK], ticks=2)
            self.assertEqual(code, 0, err)
            ge, = ev(rows, "gather_end")
            self.assertEqual((ge["tick"], ge["data"]["reason"]), (1, "docked"))
            self.assertEqual(counts(ge["data"]["inventory"]["items"]), {"bong_sung": 2, "ca_loc": 1})
            ps = [r for r in ev(rows, "phase_start") if r["tick"] == 1]
            self.assertEqual([r["phase"] for r in ps], ["quan"])
            q = [s for s in snapshots(rows) if s["phase"] == "quan"][0]
            self.assertEqual(counts(q["stock"]), {"bong_sung": 2, "ca_loc": 1})
            self.assertEqual((q["money"], q["earned"]), (200, 200))

    def test_khach_chi_goi_mon_trong_ke_hoach(self):
        with Workdir() as w:
            sc = {"gather": {"hold": as_items(["ca_loc"] * 3 + ["ca_keo"] * 4 + ["bong_sung"] * 4), "random_fish": False}}
            code, err, rows = run_day(w, scenario=sc, inputs=[DOCK], ticks=1 + 120 + 900 * 3 + 2)
            self.assertEqual(code, 0, err)
            dishes = {r["data"]["dish_id"] for r in ev(rows, "customer_arrived")}
            self.assertTrue(dishes)
            self.assertLessEqual(dishes, {"ca_loc_nuong_trui", "goi_bong_sung"})  # ca_keo_nuong ngoài kế hoạch D1

    def test_nhieu_ngay_ke_hoach_d1_den_d3_va_ca_sau_m2_tu_ngay_3(self):
        with Workdir() as w:
            code, err, rows = run_day(w, days=3, every=DAY_TICKS)
            self.assertEqual(code, 0, err)
            plans = ev(rows, "day_plan")
            self.assertEqual([(r["day"], r["tick"]) for r in plans], [(1, 0), (2, DAY_TICKS), (3, 2 * DAY_TICKS)])
            for r in plans:
                want = next(e for e in T["day_plan"] if e["day"] == r["day"])
                self.assertEqual(r["data"], {"dishes": want["dishes"], "ingredients": want["ingredients"]})
            day_start = {s["day"]: s for s in snapshots(rows) if s["phase"] == "gather" and s["phase_tick"] == 0}
            self.assertEqual([m["id"] for m in day_start[2]["monsters"]], ["M1"])
            self.assertEqual([m["id"] for m in day_start[3]["monsters"]], ["M1", "M2"])
            self.assertEqual((rows[-1]["days_completed"], rows[-1]["reason"]), (3, "days_complete"))

    def test_tick_limit_giua_ngay(self):
        with Workdir() as w:
            code, err, rows = run_day(w, days=2, ticks=DAY_TICKS + 10)
            self.assertEqual(code, 0, err)
            self.assertEqual((rows[-1]["reason"], rows[-1]["state"], rows[-1]["days_completed"]),
                             ("tick_limit", "playing", 1))

    def test_ngat_van_mo_quan_voi_kho_rong(self):
        with Workdir() as w:
            sc = {"gather": {"hold": as_items(["ca_loc"]), "random_fish": False,
                             "player": {"pos": [50, 5], "oxygen_ticks": 0, "hp": 1, "zero_oxy_ticks": 59}}}
            code, err, rows = run_day(w, scenario=sc, ticks=3)
            self.assertEqual(code, 0, err)
            ge, = ev(rows, "gather_end")
            self.assertEqual((ge["tick"], ge["data"]), (1, {"reason": "fainted", "inventory": {"items": []}}))
            self.assertEqual([r["phase"] for r in ev(rows, "phase_start") if r["tick"] == 1], ["quan"])

    def test_tat_dinh_tung_byte(self):
        with Workdir() as w:
            outs = []
            for i in (1, 2):
                code, err, _ = run_day(w, scenario=RICH, inputs=[DOCK, {"tick": 3, "move": [1, 1]}], days=2,
                                       name=f"o{i}")
                self.assertEqual(code, 0, err)
                with open(w.path(f"o{i}.jsonl"), "rb") as f:
                    outs.append(f.read())
            self.assertEqual(outs[0], outs[1])


class Shop(unittest.TestCase):
    SHOP_T = 1 + Q_TICKS  # cập bến ở tick 0 -> quán từ tick 1 -> Shop dựng ở tick 1 + Q_TICKS

    def _shop_run(self, w, shop_frames, scenario=RICH, days=2):
        return run_day(w, scenario=scenario, inputs=[DOCK, *shop_frames], days=days,
                       ticks=self.SHOP_T + S_TICKS + 5, every=1)

    def test_mua_oxy_tru_tien_hien_ngay_hieu_luc_ngay_ke(self):
        with Workdir() as w:
            t = self.SHOP_T
            code, err, rows = self._shop_run(w, [{"tick": t, "buy": "oxygen"}, {"tick": t + 1, "shop_done": True}])
            self.assertEqual(code, 0, err)
            b, = ev(rows, "bought")
            self.assertEqual((b["tick"], b["phase"], b["data"]),
                             (t + 1, "shop", {"upgrade": "oxygen", "level": 1, "price": 200, "money": 0}))
            s = next(s for s in snapshots(rows) if s["tick"] == t + 1)
            self.assertEqual((s["upgrades"], s["active_upgrades"], s["money"], s["earned"]),
                             ({"oxygen": 1}, {}, 0, 200))
            se, = ev(rows, "shop_end")
            self.assertEqual((se["tick"], se["data"], se["day"]), (t + 2, {"reason": "done"}, 1))
            d2 = [r for r in rows if r["type"] == "event" and r["tick"] == t + 2 and r["day"] == 2]
            self.assertEqual([r["name"] for r in d2], ["day_start", "day_plan", "phase_start"])
            g2 = next(s for s in snapshots(rows) if s["tick"] == t + 2)
            self.assertEqual((g2["day"], g2["phase"], g2["phase_tick"]), (2, "gather", 0))
            self.assertEqual(g2["active_upgrades"], {"oxygen": 1})
            self.assertEqual(g2["player"]["oxygen_max_ticks"], 2700)
            self.assertEqual(g2["player"]["oxygen_ticks"], 2700)
            # giỏ làm mới theo MẪU gather (v1.1 mục 4.3: mẫu khởi tạo mỗi Ngày), không cộng kho dư của Ngày 1
            self.assertEqual(counts(g2["hold"]), counts(RICH["gather"]["hold"]))  # Ngày ≥ 2: id mới (clarify #28)
            self.assertEqual((g2["player"]["hp"], g2["money"]), (T["gather"]["hp_max"], 0))

    def test_buy_failed_funds_max_level_unknown(self):
        with Workdir() as w:
            t = self.SHOP_T
            sc = {"day": {"money": 200, "earned": 200, "upgrades": {"oxygen": 2}},
                  "gather": {"random_fish": False}}
            code, err, rows = self._shop_run(w, [{"tick": t, "buy": "hp"}, {"tick": t + 1, "buy": "oxygen"},
                                                 {"tick": t + 2, "buy": "weapon"}], scenario=sc, days=1)
            self.assertEqual(code, 0, err)
            fails = [(r["data"]["action"], r["data"]["reason"]) for r in ev(rows, "buy_failed")]
            self.assertEqual(fails, [("hp", "funds"), ("oxygen", "max_level"), ("weapon", "unknown")])
            self.assertFalse(ev(rows, "bought"))
            self.assertEqual(rows[-1]["money"], 200)

    def test_du_dung_gia_van_mua_duoc_va_buy_truoc_shop_done_cung_buoc(self):
        with Workdir() as w:
            t = self.SHOP_T
            sc = {"day": {"money": 250, "earned": 250}, "gather": {"random_fish": False}}
            code, err, rows = self._shop_run(w, [{"tick": t, "buy": "hp", "shop_done": True}], scenario=sc, days=1)
            self.assertEqual(code, 0, err)
            names = [r["name"] for r in rows if r["type"] == "event" and r["tick"] == t + 1]
            self.assertEqual(names, ["bought", "shop_end"])
            self.assertEqual((rows[-1]["money"], rows[-1]["earned"], rows[-1]["reason"]), (0, 250, "days_complete"))

    def test_buy_ngoai_shop_bi_bo_qua(self):
        with Workdir() as w:
            code, err, rows = run_day(w, inputs=[{"tick": 5, "buy": "oxygen"}], ticks=20)
            self.assertEqual(code, 0, err)
            self.assertFalse(ev(rows, "bought") or ev(rows, "buy_failed"))

    def test_cap_tu_scenario_ap_dung_ngay_1(self):
        with Workdir() as w:
            code, err, rows = run_day(w, scenario={"day": {"upgrades": {"hp": 2, "oxygen": 1}}}, ticks=1)
            self.assertEqual(code, 0, err)
            s = snapshots(rows)[0]
            self.assertEqual((s["player"]["hp_max"], s["player"]["hp"], s["player"]["oxygen_max_ticks"]), (5, 5, 2700))
            self.assertEqual(s["active_upgrades"], {"hp": 2, "oxygen": 1})

    def test_day_plan_ghi_de_theo_ngay(self):
        with Workdir() as w:
            sc = {"day": {"day_plan": [{"day": 1, "dishes": {"ca_keo_nuong": 2}}]}}
            code, err, rows = run_day(w, scenario=sc, ticks=1)
            self.assertEqual(code, 0, err)
            p, = ev(rows, "day_plan")
            self.assertEqual(p["data"], {"dishes": {"ca_keo_nuong": 2}, "ingredients": {"ca_keo": 4}})


class Pause(unittest.TestCase):
    def test_pause_dung_dong_ho_va_resume_chay_ngay(self):
        with Workdir() as w:
            inp = write_json(w.path("p.json"), frames({"tick": 5, "pause": True}, {"tick": 6, "pause": False},
                                                     {"tick": 7, "interact": True}, {"tick": 8, "interact": False},
                                                     {"tick": 10, "pause": True}))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "20", "--inputs", inp,
                                     "--snapshot-every", "1", "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("g.jsonl"))
            self.assertEqual([(r["name"], r["tick"]) for r in events(rows) if r["name"] in ("paused", "resumed")],
                             [("paused", 6), ("resumed", 11)])
            self.assertFalse(events(rows, "gather_end"), "cạnh interact lúc pause (ở bến) phải bị bỏ qua")
            by = {s["tick"]: s for s in snapshots(rows)}
            self.assertEqual((by[8]["state"], by[8]["sim_tick"], by[8]["phase_tick"]), ("paused", 5, 5))
            self.assertEqual(by[8]["time_left_ticks"], by[6]["time_left_ticks"])
            self.assertEqual((by[11]["state"], by[11]["sim_tick"]), ("playing", 6))
            self.assertEqual((rows[-1]["ticks"], rows[-1]["sim_tick"]), (20, 15))

    def test_pause_trong_day_co_truong_day(self):
        with Workdir() as w:
            code, err, rows = run_day(w, inputs=[{"tick": 2, "pause": True}], ticks=5)
            self.assertEqual(code, 0, err)
            p, = ev(rows, "paused")
            self.assertEqual((p["tick"], p["phase"], p["day"]), (3, "gather", 1))
            self.assertEqual(snapshots(rows)[-1]["state"], "paused")  # `paused` chỉ có ở snapshot, end vẫn playing


class DayInputErrors(unittest.TestCase):
    def _code(self, w, *args, scenario=None, inputs=None):
        a = ["--seed", "1", "--ticks", "5", "--out", w.path("o.jsonl"), *args]
        if scenario is not None:
            a += ["--scenario", write_json(w.path("sc.json"), scenario)]
        if inputs is not None:
            a += ["--inputs", write_json(w.path("in.json"), frames(*inputs))]
        return run_headless(*a)[0]

    def test_ma_2(self):
        with Workdir() as w:
            self.assertEqual(self._code(w, "--mode", "gather", "--days", "1"), 2)
            for d in ("0", "6"):
                self.assertEqual(self._code(w, "--mode", "day", "--days", d), 2, d)
            kho = write_json(w.path("kho.json"), {"items": {}})
            self.assertEqual(self._code(w, "--mode", "day", "--inventory", kho), 2)
            self.assertEqual(self._code(w, "--mode", "day", "--inventory-out", w.path("k2.json")), 2)
            for sc in ({"quan": {"stock": {}}}, {"quan": {"reputation": 3}}, {"day": {"money": 300, "earned": 200}},
                       {"day": {"money": 100}}, {"day": {"upgrades": {"oxygen": 3}}}, {"day": {"upgrades": {"net": 1}}},
                       {"day": {"day_plan": [{"day": 1, "dishes": {"pho": 1}}]}},
                       {"day": {"day_plan": [{"day": 1, "dishes": {"goi_bong_sung": 1}, "ingredients": {"bong_sung": 3}}]}},
                       {"day": {"lives": 3}}, {"river": {}}):
                self.assertEqual(self._code(w, "--mode", "day", scenario=sc), 2, sc)
            for fr in ({"tick": 0, "buy": ""}, {"tick": 0, "buy": 5}, {"tick": 0, "pause": 1}):
                self.assertEqual(self._code(w, "--mode", "day", inputs=[fr]), 2, fr)

    def test_khach_mau_ngoai_ke_hoach_ma_2_khi_mo_quan(self):
        with Workdir() as w:
            sc = {"gather": {"hold": as_items(["ca_keo", "ca_keo"]), "random_fish": False},
                  "quan": {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_keo_nuong"}]}}
            self.assertEqual(self._code(w, "--mode", "day", scenario=sc, inputs=[DOCK]), 2)

    def test_nut_mo_rong_chua_bat_bi_bo_qua(self):
        with Workdir() as w:
            self.assertEqual(self._code(w, "--mode", "gather", inputs=[{"tick": 0, "attack": True, "photo": True}]), 0)


if __name__ == "__main__":
    unittest.main()

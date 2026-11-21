"""Test luật Phase 3 — độ tươi và kho cá thể (TICKET-03 mục 1, Test Contract v1.2), hộp đen qua headless_cmd.

Phủ: ngưỡng ươn 30 (ví dụ trong đề), hao 0.5/s ở giỏ và 0.25/s ở kho quán, id I<n> liên tục, hàng ươn vẫn chiếm ô,
giữ chỗ theo id (tươi nhất, hòa id), giữ lại khi hàng vừa ươn, giá theo tươi, bàn giao file và `day`, pause dừng hao,
fixture sai -> mã 2. Quy ước tick: bước k đọc frame tick k và ghi event ở tick k + 1.
"""

import json
import math
import unittest

from helpers import Workdir, events, frames, item, items, read_jsonl, run_headless, snapshots, write_json
from test_rules_gather import run_gather
from test_rules_gather import snap_at as gsnap
from test_rules_quan import C1_RESERVED, MENU, Q, ev, run_quan, snap_at

NO_FISH = {"random_fish": False, "monsters": []}
U = 240  # đơn vị / điểm tươi: gather -2/tick, quán -1/tick


def fresh(units):
    return units / U


def exit_code(block):
    """Chạy fixture quán THÔ (không qua adapter kho đếm của test P1)."""
    with Workdir() as w:
        sc = write_json(w.path("sc.json"), {"quan": block})
        return run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--scenario", sc, "--out", w.path("o.jsonl"))[0]


class Contract(unittest.TestCase):
    def test_contract_v12_freshness(self):
        with open("game.contract.json", encoding="utf-8") as f:
            c = json.load(f)
        self.assertIn(c["contract_version"], ("1.2", "1.3"))  # v1.3 (Phase 4) giữ nguyên gameplay/kho v1.2
        self.assertEqual(c["tuning"]["freshness"],
                         {"initial": 100, "gather_decay_per_s": 0.5, "quan_decay_per_s": 0.25, "spoiled_below": 30})


class GatherFreshness(unittest.TestCase):
    def test_vi_du_de_bai_uon_o_buoc_dau(self):
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {"hold": [item("ca_linh", "I1", 30)], **NO_FISH}})
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "1", "--scenario", sc, "--out", w.path("o.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("o.jsonl"))
        self.assertEqual(events(rows), [{"type": "event", "tick": 1, "phase": "gather", "name": "spoiled",
                                         "data": {"item_id": "I1", "kind": "ca_linh", "location": "hold"}}])

    def test_spoiled_dung_mot_lan_va_ke_dao_0(self):
        rows, _ = run_gather({"hold": [item("ca_loc", "I1", 30), item("ca_loc", "I2", 0.001)], **NO_FISH}, ticks=20)
        self.assertEqual([e["data"]["item_id"] for e in events(rows, "spoiled")], ["I1"], "I2 đã ươn sẵn: không phát")
        h = gsnap(rows, 20)["hold"]
        self.assertAlmostEqual(h[0]["fresh"], 30 - 20 * 0.5 / 60, delta=0.01)
        self.assertEqual(h[1]["fresh"], 0)

    def test_nhieu_ca_the_cung_uon_phat_theo_id(self):
        hold = [item("ca_loc", "I10", 30), item("bong_sung", "I2", 30), item("ca_linh", "I3", 31)]
        rows, _ = run_gather({"hold": hold, **NO_FISH}, ticks=1)
        self.assertEqual([e["data"]["item_id"] for e in events(rows, "spoiled")], ["I2", "I10"])
        self.assertEqual([i["id"] for i in gsnap(rows, 1)["hold"]], ["I10", "I2", "I3"], "giỏ giữ thứ tự vào giỏ")

    def test_hang_moi_fresh_100_hao_tu_buoc_sau_id_noi_tiep(self):
        block = {"player": {"pos": [12, 0]}, "hold": [item("ca_loc", "I5", 80)], **NO_FISH}
        rows, _ = run_gather(block, fr=({"tick": 0, "interact": True},), ticks=61)
        new1 = gsnap(rows, 1)["hold"][-1]
        self.assertEqual(new1, {"id": "I6", "kind": "bong_dien_dien", "fresh": 100})
        self.assertAlmostEqual(gsnap(rows, 61)["hold"][-1]["fresh"], 99.5, delta=0.01)
        self.assertAlmostEqual(gsnap(rows, 61)["hold"][0]["fresh"], 80 - 61 * 0.5 / 60, delta=0.01)

    def test_hang_uon_van_chiem_o(self):
        hold = [item("ca_loc", f"I{i}", 1) for i in range(1, 13)]
        rows, _ = run_gather({"player": {"pos": [12, 0]}, "hold": hold, **NO_FISH}, fr=({"tick": 0, "interact": True},), ticks=1)
        self.assertEqual(events(rows, "hold_full")[0]["data"]["free"], 0)

    def test_pause_dung_hao_tuoi(self):
        rows, _ = run_gather({"hold": [item("ca_loc", "I1", 100)], **NO_FISH},
                             fr=({"tick": 0, "pause": True}, {"tick": 1, "pause": False},
                                 {"tick": 10, "pause": True}), ticks=11)
        self.assertAlmostEqual(gsnap(rows, 11)["hold"][0]["fresh"], fresh(24000 - 2), delta=0.001)


class Handoff(unittest.TestCase):
    def dock(self, w, hold):
        sc = write_json(w.path("g.json"), {"gather": {"hold": hold, **NO_FISH}})
        inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
        kho = w.path("kho.json")
        code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "5", "--scenario", sc, "--inputs", inp,
                                 "--inventory-out", kho, "--out", w.path("g.jsonl"))
        self.assertEqual(code, 0, err)
        with open(kho, encoding="utf-8") as f:
            return kho, json.load(f)

    def test_smoke_ban_giao_file_theo_de(self):
        with Workdir() as w:
            kho, saved = self.dock(w, [item("ca_linh", "I1", 100)])
            self.assertEqual(saved, {"items": [{"id": "I1", "kind": "ca_linh", "fresh": fresh(24000 - 2)}]})
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--inventory", kho, "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            got = snapshots(read_jsonl(w.path("q.jsonl")))[0]["stock"]
        self.assertEqual([(i["id"], i["kind"]) for i in got], [("I1", "ca_linh")])
        self.assertAlmostEqual(got[0]["fresh"], saved["items"][0]["fresh"], delta=0.01)

    def test_nguong_30_giu_nhanh_qua_file(self):
        # 7202 đơn vị: sau 1 bước gather còn đúng 30.0 (chưa ươn); quán hao bước đầu -> 7199 < 7200 -> ươn ở stock
        with Workdir() as w:
            kho, saved = self.dock(w, [item("ca_loc", "I1", 7202 / U)])
            self.assertEqual(saved["items"][0]["fresh"], 30)
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "1", "--inventory", kho,
                                     "--scenario", write_json(w.path("q.json"), {"quan": {"random_customers": False}}),
                                     "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("q.jsonl"))
        self.assertEqual(ev(rows, "spoiled"), [(1, {"item_id": "I1", "kind": "ca_loc", "location": "stock"})])

    def test_ngat_ghi_kho_rong(self):
        with Workdir() as w:
            sc = write_json(w.path("g.json"), {"gather": {"hold": items("ca_loc"), "player": {"pos": [50, 10], "hp": 1,
                                                          "oxygen_ticks": 0, "zero_oxy_ticks": 59}, **NO_FISH}})
            kho = w.path("kho.json")
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "5", "--scenario", sc,
                                     "--inventory-out", kho, "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            with open(kho, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": []})


class QuanFreshness(unittest.TestCase):
    def test_kho_quan_hao_025_moi_giay(self):
        rows = run_quan({"stock": [item("ca_loc", "I1", 50)], "random_customers": False}, ticks=240)
        self.assertAlmostEqual(snap_at(rows, 240)["stock"][0]["fresh"], 49, delta=0.001)

    def test_giu_ca_the_tuoi_nhat_hoa_theo_id(self):
        stock = [item("ca_loc", "I1", 80), item("ca_loc", "I3", 90), item("ca_loc", "I2", 90)]
        rows = run_quan({"stock": stock}, ticks=120)
        self.assertEqual(snap_at(rows, 120)["customers"][0]["reserved"], ["I2"])

    def test_hang_uon_khong_dung_nau(self):
        rows = run_quan({"stock": [item("ca_loc", "I1", 29.9)]}, ticks=120)
        self.assertEqual(ev(rows, "no_dish"), [(120, {})])
        self.assertEqual(ev(rows, "customer_arrived"), [])

    def test_phan_giu_vua_uon_thi_giu_lai(self):
        stock = [item("ca_loc", "I1", 30), item("ca_loc", "I2", 50)]
        rows = run_quan({"stock": stock, "random_customers": False, "customers": [dict(C1_RESERVED, reserved=["I1"])]}, ticks=2)
        self.assertEqual([e["data"]["item_id"] for e in events(rows, "spoiled")], ["I1"])
        c = snap_at(rows, 1)["customers"][0]
        self.assertEqual((c["order_status"], c["reserved"]), ("reserved", ["I2"]))
        self.assertEqual(len(snap_at(rows, 1)["stock"]), 2, "hàng ươn vẫn trong kho")

    def test_giu_lai_khong_du_thi_unfulfillable_khach_van_cho(self):
        rows = run_quan({"stock": [item("ca_loc", "I1", 30)], "random_customers": False,
                         "customers": [dict(C1_RESERVED, reserved=["I1"], patience_ticks_left=3)]}, ticks=3)
        c = snap_at(rows, 1)["customers"][0]
        self.assertEqual((c["order_status"], c["reserved"], c["state"]), ("unfulfillable", [], "waiting"))
        self.assertEqual(ev(rows, "customer_left")[0][0], 3, "chờ tới hết kiên nhẫn")

    def test_don_bi_anh_huong_xu_ly_theo_order_tick_roi_id_ban(self):
        stock = [item("ca_loc", "I1", 30), item("ca_loc", "I2", 30), item("ca_loc", "I3", 60)]
        cs = [dict(C1_RESERVED, id="C1", table_id="T2", order_tick=5, reserved=["I1"]),
              dict(C1_RESERVED, id="C2", table_id="T1", order_tick=5, reserved=["I2"])]
        rows = run_quan({"stock": stock, "random_customers": False, "customers": cs}, ticks=1)
        by = {c["id"]: c for c in snap_at(rows, 1)["customers"]}
        self.assertEqual((by["C2"]["order_status"], by["C2"]["reserved"]), ("reserved", ["I3"]))
        self.assertEqual(by["C1"]["order_status"], "unfulfillable")
        self.assertEqual([e["data"]["item_id"] for e in events(rows, "spoiled")], ["I1", "I2"], "phát hết spoiled trước")

    def test_gia_theo_tuoi_va_items_la_ca_the(self):
        stock = [item("ca_loc", "I2", 100), item("bong_dien_dien", "I1", 40)]
        block = {"player": {"pos": [2, 8]}, "stock": stock, "random_customers": False,
                 "customers": [dict(C1_RESERVED, dish_id="canh_chua_ca_loc")]}
        rows = run_quan(block, fr=({"tick": 0, "interact": True},), ticks=1)
        d = ev(rows, "cook_started")[0][1]
        mean_u = ((24000 - 1) + (9600 - 1)) / 2
        want = math.floor(MENU["canh_chua_ca_loc"]["price"] * mean_u / (U * 100))
        self.assertEqual(d["base_price"], want)
        self.assertEqual(want, 62)
        self.assertEqual([(i["id"], i["kind"]) for i in d["items"]], [("I1", "bong_dien_dien"), ("I2", "ca_loc")])
        self.assertEqual(snap_at(rows, 1)["stoves"][0]["dish"]["base_price"], 62)
        self.assertEqual(snap_at(rows, 1)["stock"], [], "tiêu đúng các id đang giữ")

    def test_boa_tinh_tren_gia_da_chot(self):
        stock = [item("ca_loc", "I1", 50)]
        cook = int(MENU["ca_loc_nuong_trui"]["cook_s"] * 60)
        fr = ({"tick": 0, "interact": True}, {"tick": 1, "interact": False}, {"tick": cook + 1, "interact": True},
              {"tick": cook + 2, "interact": False, "move": [0.7, -0.6]})
        block = {"player": {"pos": [2, 8]}, "stock": stock, "random_customers": False, "customers": [C1_RESERVED]}
        rows = run_quan(block, fr=fr, ticks=cook + 2)
        base = 60 * (12000 - 1) // 24000
        self.assertEqual(ev(rows, "cook_started")[0][1]["base_price"], base)
        self.assertEqual(snap_at(rows, cook + 2)["hand"]["base_price"], base)
        self.assertEqual(math.floor(base * Q["tip_rate"]), 5)


class Fixtures(unittest.TestCase):
    def test_fixture_sai_ma_2(self):
        ok_stock = [item("ca_loc", "I1", 50), item("ca_loc", "I2", 60)]
        bad = [
            {"stock": {"ca_loc": 1}},                                                   # kho đếm cũ
            {"stock": [item("ca_loc", "I1", 101)]},
            {"stock": [item("ca_loc", "I1", 50), item("bong_sung", "I1", 50)]},         # id trùng
            {"stock": [{"id": "I1", "kind": "ca_loc"}]},                                # thiếu fresh
            {"stock": ok_stock, "customers": [dict(C1_RESERVED, reserved=["I9"])]},     # id không có trong kho
            {"stock": [item("ca_loc", "I1", 20)], "customers": [dict(C1_RESERVED, reserved=["I1"])]},  # đã ươn
            {"stock": ok_stock, "customers": [dict(C1_RESERVED, reserved=["I1"]),
                                              dict(C1_RESERVED, id="C2", table_id="T2", reserved=["I1"])]},  # dùng chung
            {"stock": [item("bong_sung", "I1", 50)], "customers": [dict(C1_RESERVED, reserved=["I1"])]},  # sai công thức
            {"stock": ok_stock, "customers": [dict(C1_RESERVED, reserved={"ca_loc": 1})]},  # kiểu cũ
            {"stock": [item("ca_loc", "I1", 20)], "customers": [C1_RESERVED]},          # không đủ hàng chưa ươn để cấp
        ]
        for block in bad:
            self.assertEqual(exit_code(block), 2, block)
        with Workdir() as w:
            for hold in (["ca_loc"], [item("ca_loc", "I1", -0.5)], [item("ca_loc", "I1", 5), item("ca_loc", "I1", 6)]):
                sc = write_json(w.path("g.json"), {"gather": {"hold": hold}})
                self.assertEqual(run_headless("--mode", "gather", "--seed", "1", "--ticks", "0", "--scenario", sc,
                                              "--out", w.path("o.jsonl"))[0], 2, hold)

    def test_thieu_reserved_cap_tuoi_nhat_theo_order_tick(self):
        stock = [item("ca_loc", "I1", 70), item("ca_loc", "I2", 90)]
        cs = [dict(C1_RESERVED, id="C1", table_id="T1", order_tick=9),
              dict(C1_RESERVED, id="C2", table_id="T2", order_tick=3)]
        rows = run_quan({"stock": stock, "random_customers": False, "customers": cs}, ticks=0)
        by = {c["id"]: c["reserved"] for c in snapshots(rows)[0]["customers"]}
        self.assertEqual(by, {"C1": ["I1"], "C2": ["I2"]})


class DayItems(unittest.TestCase):
    def test_id_tang_xuyen_ngay_va_ban_giao_cung_tick(self):
        sc = {"gather": {"hold": items("ca_loc", "bong_sung", "bong_sung"), "random_fish": False},
              "quan": {"time_left_ticks": 20, "random_customers": False}}
        with Workdir() as w:
            p = write_json(w.path("sc.json"), sc)
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            code, err = run_headless("--mode", "day", "--days", "2", "--seed", "1", "--ticks", "2000", "--scenario", p,
                                     "--inputs", inp, "--snapshot-every", "1000", "--out", w.path("d.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("d.jsonl"))
        snaps = snapshots(rows)
        ge = events(rows, "gather_end")[0]
        q0 = [s for s in snaps if s["phase"] == "quan" and s["phase_tick"] == 0][0]
        self.assertEqual(q0["tick"], ge["tick"])
        self.assertEqual(q0["stock"], ge["data"]["inventory"]["items"], "bàn giao cùng tick, không hao thêm")
        self.assertEqual([i["id"] for i in q0["stock"]], ["I1", "I2", "I3"])
        shop = [s for s in snaps if s["phase"] == "shop"][0]
        self.assertEqual([i["id"] for i in shop["stock"]], ["I1", "I2", "I3"], "kho dư hiện ở Shop")
        d2 = [s for s in snaps if s.get("day") == 2 and s["phase"] == "gather"][0]
        self.assertEqual([(i["id"], i["kind"], i["fresh"]) for i in d2["hold"]],
                         [("I4", "ca_loc", 100), ("I5", "bong_sung", 100), ("I6", "bong_sung", 100)],
                         "Ngày kế cấp id mới theo thứ tự mảng mẫu, giữ kind/fresh ban đầu")


if __name__ == "__main__":
    unittest.main()

"""Test luật Quán (PRD-0, Test Contract mục D và F "Quán"), hộp đen qua headless_cmd.

Preset v1.1: bếp B1 [2, 8], B2 [5, 8]; bàn T1 [9, 2], T2 [13, 2], T3 [9, 6], T4 [13, 6]; interact_radius 1.5,
khách đầu ở phase_tick 120, rồi mỗi 900 tick. Luật Phase 2 riêng ở test_rules_p2_quan.py.
"""

import json
import math
import unittest

from helpers import Workdir, as_items, counts, events, frames, read_jsonl, run_headless, snapshots, write_json


def tuning():
    with open("game.contract.json", encoding="utf-8") as f:
        return json.load(f)["tuning"]


Q = tuning()["quan"]
MENU = tuning()["menu"]
PATIENCE = int(Q["patience_s"] * 60)
EAT = int(Q["eat_s"] * 60)
STOVE = Q["stoves"][0]["pos"]
TABLE = Q["tables"][0]["pos"]


def _v12(block):
    """Adapter fixture P1–P2 -> v1.2: `stock` dạng đếm {kind: n} đổi sang cá thể I1… fresh 100 (sắp theo kind)."""
    if "stock" in block:
        block = dict(block, stock=as_items(block["stock"]))
    return block


def price_at(dish_id, ticks_in_stock):
    """v1.2: giá chốt khi nấu = floor(giá × fresh/100); kho quán hao 0.25/s = 1/240 điểm mỗi tick (fresh đầu 100)."""
    units = 24000 - ticks_in_stock
    return MENU[dish_id]["price"] * units // 24000


def run_quan(block, fr=(), ticks=1, seed=1):
    block = _v12(block)
    with Workdir() as w:
        args = ["--mode", "quan", "--seed", str(seed), "--ticks", str(ticks), "--snapshot-every", "1",
                "--scenario", write_json(w.path("sc.json"), {"quan": block}), "--out", w.path("o.jsonl")]
        if fr:
            args += ["--inputs", write_json(w.path("in.json"), frames(*fr))]
        code, err = run_headless(*args)
        assert code == 0, err
        return read_jsonl(w.path("o.jsonl"))


def exit_code(block):
    block = _v12(block)
    with Workdir() as w:
        sc = write_json(w.path("sc.json"), {"quan": block})
        return run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--scenario", sc, "--out", w.path("o.jsonl"))[0]


def snap_at(rows, tick):
    return {s["tick"]: s for s in snapshots(rows)}[tick]


def ev(rows, name):
    return [(e["tick"], e["data"]) for e in events(rows, name)]


def payload(order_id="C1", dish_id="ca_loc_nuong_trui"):
    return {"order_id": order_id, "dish_id": dish_id, "base_price": MENU[dish_id]["price"]}


C1_RESERVED = {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}
C1_ASSIGNED = dict(C1_RESERVED, order_status="assigned", reserved=[])  # v1.2: reserved là mảng id cá thể


class Customers(unittest.TestCase):
    def test_khach_dau_den_theo_lich_va_giu_cho(self):
        rows = run_quan({"stock": {"ca_loc": 2}}, ticks=Q["first_customer_tick"])
        self.assertEqual(ev(rows, "customer_arrived"),
                         [(120, {"order_id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"})])
        s = snap_at(rows, 120)
        c = s["customers"][0]
        self.assertEqual((c["order_tick"], c["state"], c["order_status"]), (120, "waiting", "reserved"))
        self.assertEqual(c["reserved"], ["I1"], "v1.2: giữ theo id, tươi nhất rồi id nhỏ")
        self.assertEqual(c["patience_ticks_left"], PATIENCE)
        self.assertEqual(counts(s["stock"]), {"ca_loc": 2}, "stock là tồn vật lý, gồm cả phần giữ")
        self.assertEqual(s["tables"][0]["customer_id"], "C1")

    def test_kien_nhan_giam_tu_buoc_sau(self):
        rows = run_quan({"stock": {"ca_loc": 1}}, ticks=122)
        self.assertEqual(snap_at(rows, 121)["customers"][0]["patience_ticks_left"], PATIENCE - 1)

    def test_no_dish_khi_co_ban_ma_thieu_mon(self):
        interval = int(Q["customer_interval_s"] * 60)
        rows = run_quan({}, ticks=120 + interval)
        self.assertEqual(ev(rows, "no_dish"), [(120, {}), (120 + interval, {})])

    def test_het_ban_thi_bo_luot(self):
        # v1.1 có 4 bàn: lấp kín mọi bàn bằng fixture, lượt khách tick 120 phải bị bỏ (không no_dish)
        seated = [dict(C1_RESERVED, id=f"C{i}", table_id=tb["id"]) for i, tb in enumerate(Q["tables"], 1)]
        rows = run_quan({"stock": {"ca_loc": len(seated) + 1}, "customers": seated}, ticks=120)
        self.assertEqual(events(rows, "customer_arrived"), [])
        self.assertEqual(events(rows, "no_dish"), [])

    def test_chon_mon_trong_cac_mon_du_nguyen_lieu(self):
        stock = {"ca_loc": 1, "bong_sung": 2, "ca_linh": 3, "bong_dien_dien": 1}
        seen = set()
        for seed in range(1, 9):
            rows = run_quan({"stock": stock}, ticks=120, seed=seed)
            seen.add(events(rows, "customer_arrived")[0]["data"]["dish_id"])
        self.assertTrue(seen <= set(MENU))
        self.assertGreater(len(seen), 1, "chọn đều theo seed: nhiều seed phải ra hơn một món")

    def test_random_customers_false_tat_khach_tu_sinh(self):
        rows = run_quan({"stock": {"ca_loc": 1}, "random_customers": False}, ticks=200)
        self.assertEqual(events(rows, "customer_arrived"), [])

    def test_het_kien_nhan_roi_ban_tru_uy_tin_nha_giu_cho(self):
        block = {"stock": {"ca_loc": 1}, "random_customers": False,
                 "customers": [dict(C1_RESERVED, patience_ticks_left=1)]}
        rows = run_quan(block, ticks=2)
        rep = Q["reputation_initial"] + Q["left_reputation_delta"]
        self.assertEqual(ev(rows, "customer_left"),
                         [(1, {"order_id": "C1", "table_id": "T1", "reason": "patience", "reputation": rep})])
        s = snap_at(rows, 1)
        self.assertEqual((s["customers"], s["tables"][0]["customer_id"]), ([], None))
        self.assertEqual(counts(s["stock"]), {"ca_loc": 1})
        self.assertAlmostEqual(s["reputation"], rep, places=2)

    def test_khach_roi_bo_mon_dang_nau(self):
        block = {"random_customers": False, "customers": [dict(C1_ASSIGNED, patience_ticks_left=1)],
                 "stoves": [{"id": "B1", "state": "cooking", "dish": payload(), "cook_ticks_left": 100}]}
        rows = run_quan(block, ticks=1)
        st = snap_at(rows, 1)["stoves"][0]
        self.assertEqual((st["state"], st["dish"]), ("idle", None))


class Kitchen(unittest.TestCase):
    def test_nau_tieu_nguyen_lieu_giu_va_chin_dung_tick(self):
        cook = int(MENU["ca_loc_nuong_trui"]["cook_s"] * 60)
        block = {"player": {"pos": STOVE}, "stock": {"ca_loc": 1}, "random_customers": False, "customers": [C1_RESERVED]}
        rows = run_quan(block, fr=({"tick": 0, "interact": True},), ticks=cook + 1)
        self.assertEqual(ev(rows, "cook_started"),
                         [(1, {"stove_id": "B1", "order_id": "C1", "dish_id": "ca_loc_nuong_trui",
                               "items": [{"id": "I1", "kind": "ca_loc", "fresh": 99.996}],
                               "base_price": price_at("ca_loc_nuong_trui", 1)})])  # v1.2: cá thể + giá theo tươi
        s = snap_at(rows, 1)
        self.assertEqual(s["stock"], [])
        c = s["customers"][0]
        self.assertEqual((c["order_status"], c["reserved"]), ("assigned", []))
        self.assertEqual(ev(rows, "dish_ready"),
                         [(1 + cook, {"stove_id": "B1", "order_id": "C1", "dish_id": "ca_loc_nuong_trui"})])
        st = snap_at(rows, 1 + cook)["stoves"][0]
        self.assertEqual((st["state"], st["ready_ticks"]), ("ready", 0))

    def test_ready_ticks_tang_tu_buoc_sau(self):
        block = {"random_customers": False, "customers": [C1_ASSIGNED],
                 "stoves": [{"id": "B1", "state": "cooking", "dish": payload(), "cook_ticks_left": 1}]}
        rows = run_quan(block, ticks=3)
        self.assertEqual([snap_at(rows, t)["stoves"][0]["ready_ticks"] for t in (1, 2, 3)], [0, 1, 2])

    def test_bung_mon_tu_bep_ready(self):
        block = {"player": {"pos": STOVE}, "random_customers": False, "customers": [C1_ASSIGNED],
                 "stoves": [{"id": "B1", "state": "ready", "dish": payload(), "ready_ticks": 5}]}
        rows = run_quan(block, fr=({"tick": 0, "interact": True},), ticks=1)
        self.assertEqual(ev(rows, "dish_picked"),
                         [(1, {"stove_id": "B1", "order_id": "C1", "dish_id": "ca_loc_nuong_trui"})])
        s = snap_at(rows, 1)
        self.assertEqual(s["hand"], payload())
        self.assertEqual(s["stoves"][0]["state"], "idle")

    def test_bep_idle_khong_co_don_thi_bo_luot(self):
        rows = run_quan({"player": {"pos": STOVE}, "random_customers": False},
                        fr=({"tick": 0, "interact": True},), ticks=1)
        self.assertEqual(events(rows), [])


class Serving(unittest.TestCase):
    def serve(self, patience):
        block = {"player": {"pos": TABLE}, "random_customers": False, "hand": payload(),
                 "customers": [dict(C1_ASSIGNED, patience_ticks_left=patience)]}
        return run_quan(block, fr=({"tick": 0, "interact": True},), ticks=EAT + 2)

    def test_phuc_vu_boa_khi_kien_nhan_du_ty_le(self):
        rows = self.serve(PATIENCE)
        tip = math.floor(60 * Q["tip_rate"])
        self.assertEqual(ev(rows, "served"),
                         [(1, {"order_id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                               "patience_ticks_left": PATIENCE - 1, "base_price": 60, "tip": tip})])
        self.assertEqual(ev(rows, "paid"),
                         [(1 + EAT, {"order_id": "C1", "table_id": "T1", "base_price": 60, "tip": tip,
                                     "amount": 60 + tip, "reason": "finished_eating"})])
        end = rows[-1]
        rep = Q["reputation_initial"] + Q["tip_reputation"]
        self.assertEqual((end["money"], end["earned"]), (60 + tip, 60 + tip))
        self.assertAlmostEqual(end["reputation"], rep, places=2)
        self.assertEqual(end["score"], 60 + tip + 100 * math.floor(rep))
        self.assertEqual(snap_at(rows, 1 + EAT)["customers"], [])

    def test_kien_nhan_thap_khong_boa(self):
        low = int(PATIENCE * Q["tip_min_patience_ratio"])  # sau bước 1 còn low - 1 < ngưỡng
        rows = self.serve(low)
        self.assertEqual(events(rows, "served")[0]["data"]["tip"], 0)
        self.assertEqual(events(rows, "paid")[0]["data"]["amount"], 60)
        self.assertAlmostEqual(rows[-1]["reputation"], Q["reputation_initial"], places=2)

    def test_dung_nguong_ty_le_van_boa(self):
        at = int(PATIENCE * Q["tip_min_patience_ratio"]) + 1  # sau bước 1 còn đúng ngưỡng
        self.assertGreater(events(self.serve(at), "served")[0]["data"]["tip"], 0)

    def test_phuc_vu_dung_tick_kien_nhan_ve_0_van_hop_le(self):
        rows = self.serve(1)
        self.assertEqual(len(events(rows, "served")), 1)
        self.assertEqual(events(rows, "customer_left"), [])

    def test_ban_sai_mon_khong_phuc_vu(self):
        block = {"player": {"pos": TABLE}, "random_customers": False, "hand": None,
                 "customers": [C1_RESERVED], "stock": {"ca_loc": 1}}
        rows = run_quan(block, fr=({"tick": 0, "interact": True},), ticks=1)
        self.assertEqual(events(rows, "served"), [])

    def test_bep_truoc_ban_khi_bang_khoang_cach_va_bo_luot(self):
        """Bếp và bàn cách đều: chọn bếp; bếp idle không có đơn -> bỏ lượt, KHÔNG phục vụ bàn."""
        tables = [{"id": "T1", "pos": [STOVE[0] + 1, STOVE[1]]}]
        block = {"player": {"pos": [STOVE[0] + 0.5, STOVE[1]]}, "random_customers": False, "hand": payload(),
                 "customers": [C1_ASSIGNED], "tables": tables}
        rows = run_quan(block, fr=({"tick": 0, "interact": True},), ticks=1)
        self.assertEqual(events(rows, "served"), [])
        block["player"] = {"pos": [STOVE[0] + 0.9, STOVE[1]]}
        rows = run_quan(block, fr=({"tick": 0, "interact": True},), ticks=1)
        self.assertEqual(len(events(rows, "served")), 1)


class Closing(unittest.TestCase):
    def test_het_ca_khach_dang_an_tra_ngay(self):
        block = {"time_left_ticks": 1, "random_customers": False,
                 "customers": [dict(C1_RESERVED, state="eating", order_status="served", reserved=[],
                                    eat_ticks_left=100, base_price=60, tip=12)]}
        rows = run_quan(block, ticks=5)
        self.assertEqual([e["name"] for e in events(rows)], ["paid", "quan_end"])
        self.assertEqual(events(rows, "paid")[0]["data"]["reason"], "closing")
        end = events(rows, "quan_end")[0]["data"]
        self.assertEqual((end["reason"], end["money"], end["earned"], end["shift_earned"]), ("time", 72, 72, 72))
        self.assertEqual(rows[-1]["reason"], "time")

    def test_het_ca_khach_cho_roi_closing_khong_tru_uy_tin(self):
        block = {"time_left_ticks": 1, "random_customers": False, "stock": {"ca_loc": 1},
                 "customers": [dict(C1_RESERVED, patience_ticks_left=1)]}
        rows = run_quan(block, ticks=5)
        left = events(rows, "customer_left")[0]["data"]
        self.assertEqual((left["reason"], left["reputation"]), ("closing", Q["reputation_initial"]))
        self.assertEqual(rows[-1]["ticks"], 1)


class FullShift(unittest.TestCase):
    def test_nau_bung_phuc_vu_tra_tien(self):
        cook = int(MENU["ca_loc_nuong_trui"]["cook_s"] * 60)
        dx, dz = TABLE[0] - STOVE[0], TABLE[1] - STOVE[1]
        n = math.hypot(dx, dz)
        walk = int(math.ceil(n / Q["walk_speed"] * 60))
        t_pick, t_go = cook + 1, cook + 2
        t_stop = t_go + walk
        fr = ({"tick": 0, "interact": True}, {"tick": 1, "interact": False}, {"tick": t_pick, "interact": True},
              {"tick": t_go, "interact": False, "move": [dx / n, dz / n]}, {"tick": t_stop, "move": [0, 0]},
              {"tick": t_stop + 10, "interact": True})
        block = {"player": {"pos": STOVE}, "stock": {"ca_loc": 1}, "random_customers": False, "customers": [C1_RESERVED]}
        rows = run_quan(block, fr=fr, ticks=t_stop + 12 + EAT)
        names = [e["name"] for e in events(rows)]
        self.assertEqual(names, ["cook_started", "dish_ready", "dish_picked", "served", "paid"])
        base = price_at("ca_loc_nuong_trui", 1)  # v1.2: nấu ở tick 1 -> 59 (không còn giá niêm yết 60)
        self.assertEqual(rows[-1]["earned"], base + math.floor(base * Q["tip_rate"]))


class FixtureContradictions(unittest.TestCase):
    def test_mau_thuan_tra_ma_2(self):
        bad = [
            {"stock": {"ca_loc": 2}, "customers": [dict(C1_RESERVED, reserved=["I1", "I2"])]},  # khác công thức
            {"customers": [C1_RESERVED]},  # giữ quá tồn (kho rỗng)
            {"hand": payload("C9")},  # liên kết thiếu
            {"customers": [C1_ASSIGNED]},  # assigned không có món
            {"customers": [dict(C1_ASSIGNED, state="eating", order_status="served", eat_ticks_left=5)]},  # thiếu giá/tip
            {"customers": [C1_ASSIGNED], "stoves": [{"id": "B1", "state": "cooking", "dish": payload()}]},  # timer 0
            {"customers": [C1_ASSIGNED], "hand": payload(dish_id="goi_bong_sung")},  # món không khớp đơn
            {"customers": [C1_ASSIGNED], "hand": payload(),
             "stoves": [{"id": "B1", "state": "ready", "dish": payload()}]},  # bếp và tay cùng đơn
            {"customers": [dict(C1_RESERVED, mood="vui")], "stock": {"ca_loc": 1}},  # trường lạ
            {"customers": [dict(C1_RESERVED, dish_id="pho")]},  # món ngoài phạm vi
            {"customers": [dict(C1_RESERVED, order_status="unfulfillable", reserved=["I1"])],
             "stock": {"ca_loc": 1}},  # unfulfillable phải giữ rỗng
            {"stoves": [{"id": "B9"}]},  # bếp không tồn tại (v1.1 đã có B2 thật)
            {"reputation": 9},
        ]
        for block in bad:
            self.assertEqual(exit_code(block), 2, block)

    def test_fixture_hop_le(self):
        good = [
            {"stock": {"ca_loc": 1}, "customers": [C1_RESERVED]},
            {"customers": [C1_ASSIGNED], "hand": payload()},
            {"customers": [dict(C1_RESERVED, order_status="unfulfillable")]},
        ]
        for block in good:
            self.assertEqual(exit_code(block), 0, block)

    def test_thieu_reserved_thi_cap_theo_cong_thuc(self):
        rows = run_quan({"stock": {"ca_loc": 1}, "customers": [C1_RESERVED], "random_customers": False}, ticks=0)
        self.assertEqual(snapshots(rows)[0]["customers"][0]["reserved"], ["I1"])


class Determinism(unittest.TestCase):
    def test_quan_cung_seed_giong_tung_byte(self):
        stock = {"ca_loc": 3, "bong_sung": 4, "ca_linh": 3, "bong_dien_dien": 1}
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"quan": _v12({"stock": stock})})
            for i in (1, 2):
                code, err = run_headless("--mode", "quan", "--seed", "5", "--ticks", "2000", "--scenario", sc,
                                         "--out", w.path(f"o{i}.jsonl"))
                self.assertEqual(code, 0, err)
            with open(w.path("o1.jsonl"), "rb") as a, open(w.path("o2.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())


if __name__ == "__main__":
    unittest.main()

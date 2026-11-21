"""Mở rộng Cháy món (`burn`), TICKET-02 mục 3 + Test Contract v1.1 mục 4.1/4.4/4.5.

Luật: `burn_s: 20`. Món chín có `ready_ticks > 1200` thì bỏ món (nguyên liệu đã tiêu, không hoàn), bếp rảnh ngay,
thử giữ lại ngay cho đơn: đủ -> `reserved`, thiếu -> `unfulfillable` (khách tiếp tục chờ). Đúng 1.200 tick vẫn bưng
được. Xét chín/cháy theo id bếp, trước di chuyển và tương tác. Event `dish_burnt {stove_id, order_id, dish_id,
order_status sau xử lý}`. Hộp đen qua headless_cmd; riêng kiểm manifest gọi thẳng `chonoi.contract`.
"""

import copy
import json
import unittest

from chonoi.contract import load_contract, validate_extensions
from chonoi.errors import BadInput
from helpers import counts, events
from test_rules_quan import MENU, PATIENCE, Q, STOVE, ev, payload, run_quan, snap_at

BURN = int(Q["burn_s"] * 60)
DISH = "ca_loc_nuong_trui"
C1 = {"id": "C1", "table_id": "T1", "dish_id": DISH, "order_status": "assigned", "reserved": []}
C2 = dict(C1, id="C2", table_id="T2")


def ready_stove(sid="B1", order_id="C1", age=BURN):
    """Bếp có món đã chín `age` tick (ready_ticks dựng tuổi món chín, v1.1 mục 4.3)."""
    return {"id": sid, "state": "ready", "dish": payload(order_id), "ready_ticks": age}


def burnt(stove_id, order_id, status):
    return {"stove_id": stove_id, "order_id": order_id, "dish_id": DISH, "order_status": status}


class Manifest(unittest.TestCase):
    def test_khai_burn_trong_extensions(self):
        with open("game.contract.json", encoding="utf-8") as f:
            c = json.load(f)
        self.assertEqual(c["extensions"], ["burn"])
        self.assertEqual((Q["burn_s"], BURN), (20, 1200))

    def test_burn_s_phai_khop_extensions(self):
        base = load_contract()

        def check(ext, burn_s):
            c = copy.deepcopy(base)
            c["extensions"], c["tuning"]["quan"]["burn_s"] = ext, burn_s
            validate_extensions(c)

        check(["burn"], 20)
        check([], None)  # lõi
        for ext, burn_s in ((["burn"], None), (["burn"], 0), (["burn"], float("inf")), ([], 20),
                            (["burn", "burn"], 20), (["xyz"], None), (["current"], None), ("burn", 20)):
            with self.subTest(ext=ext, burn_s=burn_s), self.assertRaises(BadInput):
                check(ext, burn_s)


class Burn(unittest.TestCase):
    def test_dung_1200_tick_van_bung_duoc(self):
        block = {"player": {"pos": STOVE}, "random_customers": False, "customers": [C1],
                 "stoves": [ready_stove(age=BURN - 1)]}  # sau đầu bước 1: ready_ticks = 1200
        rows = run_quan(block, fr=({"tick": 0, "interact": True},), ticks=1)
        self.assertEqual(events(rows, "dish_burnt"), [])
        self.assertEqual(ev(rows, "dish_picked"), [(1, {"stove_id": "B1", "order_id": "C1", "dish_id": DISH})])
        self.assertEqual(snap_at(rows, 1)["hand"], payload())

    def test_qua_1200_tick_thi_chay_va_giu_lai_cho_don(self):
        block = {"stock": {"ca_loc": 1}, "random_customers": False, "customers": [C1], "stoves": [ready_stove()]}
        rows = run_quan(block, ticks=1)  # 1200 -> 1201 > 1200
        self.assertEqual(ev(rows, "dish_burnt"), [(1, burnt("B1", "C1", "reserved"))])
        s = snap_at(rows, 1)
        st = s["stoves"][0]
        self.assertEqual((st["state"], st["dish"], st["cook_ticks_left"], st["ready_ticks"]), ("idle", None, 0, 0))
        c = s["customers"][0]
        self.assertEqual((c["state"], c["order_status"], c["reserved"], c["base_price"]),
                         ("waiting", "reserved", ["I1"], None))
        self.assertEqual(counts(s["stock"]), {"ca_loc": 1}, "món cháy không hoàn nguyên liệu; I1 là hàng có sẵn")

    def test_thieu_nguyen_lieu_thi_unfulfillable_khach_van_cho(self):
        block = {"random_customers": False, "customers": [dict(C1, patience_ticks_left=5)], "stoves": [ready_stove()]}
        rows = run_quan(block, ticks=6)
        self.assertEqual(ev(rows, "dish_burnt"), [(1, burnt("B1", "C1", "unfulfillable"))])
        c = snap_at(rows, 1)["customers"][0]
        self.assertEqual((c["state"], c["order_status"], c["reserved"], c["patience_ticks_left"]),
                         ("waiting", "unfulfillable", [], 4))
        self.assertEqual([e["tick"] for e in events(rows, "customer_left")], [5], "chờ tới hết kiên nhẫn mới rời")
        self.assertEqual(events(rows, "customer_left")[0]["data"]["reason"], "patience")

    def test_chay_truoc_tuong_tac_nen_khong_bung_duoc(self):
        block = {"player": {"pos": STOVE}, "random_customers": False, "customers": [C1], "stoves": [ready_stove()]}
        rows = run_quan(block, fr=({"tick": 0, "interact": True},), ticks=1)
        self.assertEqual([e["name"] for e in events(rows)], ["dish_burnt"])
        self.assertIsNone(snap_at(rows, 1)["hand"])

    def test_chay_roi_nau_lai_ngay_trong_cung_buoc(self):
        block = {"player": {"pos": STOVE}, "stock": {"ca_loc": 1}, "random_customers": False, "customers": [C1],
                 "stoves": [ready_stove()]}
        rows = run_quan(block, fr=({"tick": 0, "interact": True},), ticks=1)
        self.assertEqual([e["name"] for e in events(rows)], ["dish_burnt", "cook_started"])
        self.assertEqual(events(rows, "cook_started")[0]["data"]["order_id"], "C1")
        c = snap_at(rows, 1)["customers"][0]
        self.assertEqual(c["order_status"], "assigned")
        self.assertIsNotNone(c["base_price"], "giá chốt lại ở lần nấu mới")

    def test_tu_luc_chin_toi_luc_chay_dung_tick(self):
        block = {"random_customers": False, "customers": [C1],
                 "stoves": [{"id": "B1", "state": "cooking", "dish": payload(), "cook_ticks_left": 1}]}
        rows = run_quan(block, ticks=BURN + 2)  # chín ở tick 1 (ready_ticks 0), tick t có ready_ticks t-1
        self.assertEqual([e["tick"] for e in events(rows, "dish_ready")], [1])
        st = snap_at(rows, BURN + 1)["stoves"][0]
        self.assertEqual((st["state"], st["ready_ticks"]), ("ready", BURN))
        self.assertEqual(ev(rows, "dish_burnt"), [(BURN + 2, burnt("B1", "C1", "unfulfillable"))])

    def test_hai_bep_xet_theo_id_bep(self):
        # B1 giữ món của C2, B2 giữ món của C1; chỉ đủ 1 cá lóc: đơn của bếp id nhỏ (B1 -> C2) được giữ trước
        block = {"stock": {"ca_loc": 1}, "random_customers": False, "customers": [C1, C2],
                 "stoves": [ready_stove("B1", "C2"), ready_stove("B2", "C1")]}
        rows = run_quan(block, ticks=1)
        self.assertEqual(ev(rows, "dish_burnt"),
                         [(1, burnt("B1", "C2", "reserved")), (1, burnt("B2", "C1", "unfulfillable"))])
        by_id = {c["id"]: c for c in snap_at(rows, 1)["customers"]}
        self.assertEqual((by_id["C2"]["reserved"], by_id["C1"]["reserved"]), (["I1"], []))

    def test_mon_tren_tay_khong_chay(self):
        block = {"random_customers": False, "customers": [C1], "hand": payload()}
        rows = run_quan(block, ticks=BURN + 5)
        self.assertEqual(events(rows, "dish_burnt"), [])
        self.assertEqual(snap_at(rows, BURN + 5)["hand"], payload())

    def test_kien_nhan_du_lau_de_chay(self):
        self.assertGreater(PATIENCE, BURN, "preset: khách chờ 60 s > 20 s cháy, nên món cháy khi khách còn ngồi")


if __name__ == "__main__":
    unittest.main()

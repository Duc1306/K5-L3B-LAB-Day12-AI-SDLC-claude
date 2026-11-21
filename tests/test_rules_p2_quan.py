"""Test luật Quán Phase 2 (TICKET-02 mục 1.3 và 2, Test Contract v1.1): 2 bếp / 4 bàn, 6 món theo dữ liệu,
kế hoạch ngày D1–D5, lọc thực đơn theo kế hoạch (cho chế độ `day`), bàn giao kho có nguyên liệu mới.
"""

import json
import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.sim.plan import ingredients_for, plan_for_day
from chonoi.sim.quan import QuanSim

from helpers import Workdir, as_items, counts, events, frames, items, read_jsonl, run_headless, snapshots, write_json
from test_rules_quan import C1_RESERVED, ev, price_at, run_quan, snap_at

T = load_contract()["tuning"]
Q, MENU = T["quan"], T["menu"]
IDLE = InputState((0.0, 0.0), {}, set())


class StandardData(unittest.TestCase):
    def test_bep_ban_chuan(self):
        self.assertEqual([(s["id"], s["pos"]) for s in Q["stoves"]], [("B1", [2, 8]), ("B2", [5, 8])])
        self.assertEqual([(t["id"], t["pos"]) for t in Q["tables"]],
                         [("T1", [9, 2]), ("T2", [13, 2]), ("T3", [9, 6]), ("T4", [13, 6])])
        self.assertEqual((Q["first_customer_tick"], int(Q["customer_interval_s"] * 60), Q["patience_s"], Q["eat_s"]),
                         (120, 900, 60, 10))
        self.assertEqual(Q["burn_s"], 20)  # mở rộng Cháy món đã bật (lõi: null), xem test_ext_burn.py

    def test_thuc_don_6_mon(self):
        want = {
            "ca_loc_nuong_trui": ({"ca_loc": 1}, 6, 60),
            "goi_bong_sung": ({"bong_sung": 2}, 4, 40),
            "lau_ca_linh_dien_dien": ({"ca_linh": 3, "bong_dien_dien": 1}, 10, 120),
            "canh_chua_ca_loc": ({"ca_loc": 1, "bong_dien_dien": 1}, 8, 90),
            "ca_keo_nuong": ({"ca_keo": 2}, 6, 70),
            "lau_mam": ({"ca_linh": 2, "ca_keo": 1, "keo_neo": 1, "bong_dien_dien": 1}, 12, 200),
        }
        self.assertEqual({k: (d["recipe"], d["cook_s"], d["price"]) for k, d in MENU.items()}, want)

    def test_ke_hoach_D1_D5(self):
        dishes = [
            {"ca_loc_nuong_trui": 3, "goi_bong_sung": 3},
            {"ca_loc_nuong_trui": 2, "lau_ca_linh_dien_dien": 2},
            {"goi_bong_sung": 2, "canh_chua_ca_loc": 2, "ca_keo_nuong": 2},
            {"lau_mam": 1, "ca_loc_nuong_trui": 2, "goi_bong_sung": 1},
            {"lau_mam": 1, "lau_ca_linh_dien_dien": 1, "ca_loc_nuong_trui": 1},
        ]
        slots = [9, 10, 12, 9, 10]  # số ô cần (TICKET-02 bảng kế hoạch)
        self.assertEqual([e["day"] for e in T["day_plan"]], [1, 2, 3, 4, 5])
        for e, d, n in zip(T["day_plan"], dishes, slots):
            self.assertEqual(e["dishes"], d)
            self.assertEqual(e["ingredients"], ingredients_for(MENU, d))
            self.assertEqual(sum(e["ingredients"].values()), n, e["day"])
            self.assertEqual(plan_for_day(T, e["day"])["ingredients"], ingredients_for(MENU, d))
        self.assertEqual(T["day_plan"][0]["ingredients"], {"ca_loc": 3, "bong_sung": 6})

    def test_shop_chuan(self):
        ups = T["shop"]["upgrades"]
        self.assertEqual(T["shop"]["max_ticks"], 600)
        self.assertEqual([(u["price"], u["oxygen_max_s"]) for u in ups["oxygen"]], [(200, 45), (400, 60)])
        self.assertEqual([(u["price"], u["hp_max"]) for u in ups["hp"]], [(250, 4), (500, 5)])


class TwoStovesFourTables(unittest.TestCase):
    def test_khach_ngoi_ban_trong_id_nho_nhat(self):
        rows = run_quan({"stock": {"ca_loc": 2}, "customers": [C1_RESERVED]}, ticks=120)
        self.assertEqual(ev(rows, "customer_arrived"), [(120, {"order_id": "C2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui"})])

    def test_bon_ban_lap_dan_theo_lich(self):
        rows = run_quan({"stock": {"ca_loc": 9}}, ticks=2820)
        got = [(t, d["table_id"]) for t, d in ev(rows, "customer_arrived")]
        self.assertEqual(got, [(120, "T1"), (1020, "T2"), (1920, "T3"), (2820, "T4")])

    def test_nau_o_bep_B2(self):
        block = {"player": {"pos": [5, 8]}, "stock": {"ca_loc": 1}, "random_customers": False, "customers": [C1_RESERVED]}
        rows = run_quan(block, fr=({"tick": 0, "interact": True},), ticks=1)
        self.assertEqual(ev(rows, "cook_started")[0][1]["stove_id"], "B2")

    def test_bep_lay_don_cu_nhat_roi_id_ban(self):
        cs = [dict(C1_RESERVED, id="C1", table_id="T2", order_tick=5),
              dict(C1_RESERVED, id="C2", table_id="T1", order_tick=5),
              dict(C1_RESERVED, id="C3", table_id="T3", order_tick=7)]
        block = {"player": {"pos": [2, 8]}, "stock": {"ca_loc": 3}, "random_customers": False, "customers": cs}
        rows = run_quan(block, fr=({"tick": 0, "interact": True},), ticks=1)
        self.assertEqual(ev(rows, "cook_started")[0][1]["order_id"], "C2")

    def test_hai_bep_nau_song_song_hoa_theo_id(self):
        cs = [dict(C1_RESERVED, id="C1", table_id="T1", order_tick=1),
              dict(C1_RESERVED, id="C2", table_id="T2", order_tick=2)]
        # đứng giữa hai bếp (cách đều 1.5 m): chọn B1 theo id; bấm lần hai B1 đang nấu -> bỏ lượt
        fr = ({"tick": 0, "interact": True}, {"tick": 1, "interact": False}, {"tick": 2, "interact": True},
              {"tick": 3, "interact": False, "move": [1, 0]}, {"tick": 30, "move": [0, 0]}, {"tick": 40, "interact": True})
        block = {"player": {"pos": [3.5, 8]}, "stock": {"ca_loc": 2}, "random_customers": False, "customers": cs}
        rows = run_quan(block, fr=fr, ticks=41)
        self.assertEqual([(t, d["stove_id"], d["order_id"]) for t, d in ev(rows, "cook_started")],
                         [(1, "B1", "C1"), (41, "B2", "C2")])
        self.assertEqual([s["state"] for s in snap_at(rows, 41)["stoves"]], ["cooking", "cooking"])

    def test_mon_moi_lau_mam_nau_12s(self):
        stock = {"ca_linh": 2, "ca_keo": 1, "keo_neo": 1, "bong_dien_dien": 1}
        rows = run_quan({"stock": stock}, ticks=120)
        self.assertEqual(ev(rows, "customer_arrived")[0][1]["dish_id"], "lau_mam")
        cook = int(MENU["lau_mam"]["cook_s"] * 60)
        block = {"player": {"pos": [2, 8]}, "stock": stock, "random_customers": False,
                 "customers": [dict(C1_RESERVED, dish_id="lau_mam")]}
        rows = run_quan(block, fr=({"tick": 0, "interact": True},), ticks=cook + 1)
        started = ev(rows, "cook_started")[0][1]
        # v1.2: items là cá thể sắp theo kind rồi id; giá chốt theo tươi (nấu ở tick 1)
        self.assertEqual(([i["kind"] for i in started["items"]], [i["id"] for i in started["items"]], started["base_price"]),
                         (["bong_dien_dien", "ca_keo", "ca_linh", "ca_linh", "keo_neo"], ["I1", "I2", "I3", "I4", "I5"],
                          price_at("lau_mam", 1)))
        self.assertEqual([t for t, _ in ev(rows, "dish_ready")], [1 + cook])


class PlanFilter(unittest.TestCase):
    """Chế độ `day` lọc món theo kế hoạch trước khi lọc nguyên liệu (v1.1 mục 4.5). Gọi thẳng QuanSim."""

    def shift(self, stock, plan, ticks=120, seed=1, customers=()):
        sim = QuanSim(T, {"stock": as_items(stock), "customers": list(customers)}, Streams(seed), IdAllocator(),
                      plan_dishes=plan)
        out = []
        for _ in range(ticks):
            out += sim.step(IDLE)
        return out

    def test_chi_goi_mon_trong_ke_hoach(self):
        plan = plan_for_day(T, 1)["dishes"]
        stock = {"ca_loc": 5, "bong_sung": 6, "ca_linh": 6, "bong_dien_dien": 3}
        seen = set()
        for seed in range(1, 13):
            arrived = [d for n, d in self.shift(stock, plan, seed=seed) if n == "customer_arrived"]
            seen.add(arrived[0]["dish_id"])
        self.assertEqual(seen, set(plan))

    def test_mon_ngoai_ke_hoach_thi_no_dish(self):
        evs = self.shift({"ca_linh": 3, "bong_dien_dien": 1}, plan_for_day(T, 1)["dishes"])
        self.assertEqual([n for n, _ in evs], ["no_dish"])

    def test_quan_rieng_dung_ca_6_mon(self):
        evs = self.shift({"ca_linh": 3, "bong_dien_dien": 1}, None)
        self.assertEqual([d["dish_id"] for n, d in evs if n == "customer_arrived"], ["lau_ca_linh_dien_dien"])

    def test_fixture_khach_goi_mon_ngoai_ke_hoach_la_mau_thuan(self):
        with self.assertRaises(BadInput):
            self.shift({"ca_keo": 2}, plan_for_day(T, 1)["dishes"], ticks=0,
                       customers=[dict(C1_RESERVED, dish_id="ca_keo_nuong")])


class HandoffNewKinds(unittest.TestCase):
    def test_gather_sang_quan_voi_ca_keo_keo_neo(self):
        hold = ["ca_linh", "ca_linh", "ca_keo", "keo_neo", "bong_dien_dien"]
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"gather": {"hold": items(*hold), "random_fish": False, "fish": []}})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            inv = w.path("inv.json")
            code, err = run_headless("--mode", "gather", "--seed", "3", "--ticks", "1", "--scenario", sc, "--inputs", inp,
                                     "--inventory-out", inv, "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(counts(json.load(f)["items"]), {"bong_dien_dien": 1, "ca_keo": 1, "ca_linh": 2, "keo_neo": 1})
            code, err = run_headless("--mode", "quan", "--seed", "3", "--ticks", "120", "--inventory", inv,
                                     "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            rows = read_jsonl(w.path("q.jsonl"))
            self.assertEqual(counts(snapshots(rows)[0]["stock"]), {"bong_dien_dien": 1, "ca_keo": 1, "ca_linh": 2, "keo_neo": 1})
            self.assertEqual([e["data"]["dish_id"] for e in events(rows, "customer_arrived")], ["lau_mam"])


if __name__ == "__main__":
    unittest.main()

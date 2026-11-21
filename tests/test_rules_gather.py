"""Test luật Gather (PRD-0, Test Contract mục F "Gather"), hộp đen qua headless_cmd.

Quy ước tick: bước k đọc frame tick k và ghi event ở tick k + 1.
"""

import json
import unittest

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json


def tuning():
    with open("game.contract.json", encoding="utf-8") as f:
        return json.load(f)["tuning"]["gather"]


def run_gather(block, fr=(), ticks=1, inventory_out=False):
    """Chạy gather với scenario `block` và các frame; trả (rows, inventory|None)."""
    with Workdir() as w:
        args = ["--mode", "gather", "--seed", "1", "--ticks", str(ticks), "--snapshot-every", "1",
                "--scenario", write_json(w.path("sc.json"), {"gather": block}), "--out", w.path("o.jsonl")]
        if fr:
            args += ["--inputs", write_json(w.path("in.json"), frames(*fr))]
        if inventory_out:
            args += ["--inventory-out", w.path("inv.json")]
        code, err = run_headless(*args)
        assert code == 0, err
        rows = read_jsonl(w.path("o.jsonl"))
        inv = None
        if inventory_out:
            try:
                with open(w.path("inv.json"), encoding="utf-8") as f:
                    inv = json.load(f)
            except FileNotFoundError:
                inv = None
        return rows, inv


def snap_at(rows, tick):
    return {s["tick"]: s for s in snapshots(rows)}[tick]


NO_FISH = {"fish": [], "random_fish": False}


class Oxygen(unittest.TestCase):
    def test_duoi_nuoc_tru_1_tick(self):
        rows, _ = run_gather({"player": {"pos": [50, 10]}, **NO_FISH}, ticks=10)
        omax = int(tuning()["oxygen_max_s"] * 60)
        self.assertEqual(snap_at(rows, 10)["player"]["oxygen_ticks"], omax - 10)

    def test_mat_nuoc_hoi_va_kep_max(self):
        omax = int(tuning()["oxygen_max_s"] * 60)
        refill = tuning()["oxygen_refill_per_tick"]
        rows, _ = run_gather({"player": {"pos": [50, 0], "oxygen_ticks": omax - refill - 1}, **NO_FISH}, ticks=2)
        self.assertEqual(snap_at(rows, 1)["player"]["oxygen_ticks"], omax - 1)
        self.assertEqual(snap_at(rows, 2)["player"]["oxygen_ticks"], omax)

    def test_dive_va_surface_chi_khi_doi_phia(self):
        rows, _ = run_gather({"player": {"pos": [50, 0]}, **NO_FISH},
                             fr=({"tick": 0, "move": [0, 1]}, {"tick": 30, "move": [0, -1]}), ticks=90)
        dives, surfs = events(rows, "dive"), events(rows, "surface")
        self.assertEqual(len(dives), 1)
        self.assertEqual(len(surfs), 1)
        self.assertGreater(dives[0]["data"]["pos"][1], tuning()["surface_depth"])
        self.assertLessEqual(surfs[0]["data"]["pos"][1], tuning()["surface_depth"])
        self.assertLess(dives[0]["tick"], surfs[0]["tick"])

    def test_oxygen_empty_roi_choke_o_t_cong_59(self):
        rows, _ = run_gather({"player": {"pos": [50, 10], "oxygen_ticks": 1}, **NO_FISH}, ticks=70)
        empty = events(rows, "oxygen_empty")
        self.assertEqual([(e["tick"], e["data"]) for e in empty], [(1, {"oxygen_ticks": 0})])
        chokes = events(rows, "choke")
        self.assertEqual([(e["tick"], e["data"]) for e in chokes], [(60, {"hp": tuning()["hp_max"] - 1})])
        self.assertEqual(snap_at(rows, 60)["player"]["zero_oxy_ticks"], 0)

    def test_noi_len_dung_buoc_ngat_thi_khong_ngat(self):
        # đang bơi lên sẵn với vận tốc đầy: bước đầu d đi từ 0.55 xuống ~0.483 <= 0.5 (nổi lên)
        speed = tuning()["swim_speed"]
        block = {"player": {"pos": [50, 0.55], "vel": [0, -speed], "oxygen_ticks": 0, "zero_oxy_ticks": 59}, **NO_FISH}
        rows, _ = run_gather(block, fr=({"tick": 0, "move": [0, -1]},), ticks=3)
        self.assertEqual(events(rows, "surface")[0]["tick"], 1)
        self.assertEqual(events(rows, "choke"), [])
        p = snap_at(rows, 1)["player"]
        self.assertEqual(p["zero_oxy_ticks"], 0)
        self.assertEqual(p["hp"], tuning()["hp_max"])
        self.assertEqual(p["oxygen_ticks"], tuning()["oxygen_refill_per_tick"])

    def test_noi_len_reset_dem_ngat(self):
        rows, _ = run_gather({"player": {"pos": [50, 0.5], "oxygen_ticks": 0}, **NO_FISH}, ticks=1)
        p = snap_at(rows, 1)["player"]
        self.assertEqual(p["oxygen_ticks"], tuning()["oxygen_refill_per_tick"])
        self.assertEqual(p["zero_oxy_ticks"], 0)
        self.assertTrue(p["at_surface"])

    def test_ngat_mat_gio_LIFO_va_kho_rong(self):
        block = {"player": {"pos": [50, 10], "oxygen_ticks": 0, "zero_oxy_ticks": 59, "hp": 1},
                 "hold": ["ca_loc", "bong_sung", "ca_linh"], **NO_FISH}
        rows, inv = run_gather(block, ticks=10, inventory_out=True)
        names = [e["name"] for e in events(rows) if e["tick"] == 1]
        self.assertEqual(names, ["choke", "faint", "gather_end"])
        faint = events(rows, "faint")[0]["data"]
        self.assertEqual(faint, {"cause": "choke", "lost": ["ca_linh", "bong_sung", "ca_loc"], "hp": 0})
        end = events(rows, "gather_end")[0]["data"]
        self.assertEqual(end, {"reason": "fainted", "inventory": {"items": {}}})
        self.assertEqual(inv, {"items": {}})
        self.assertEqual(rows[-1]["reason"], "fainted")
        self.assertEqual(rows[-1]["ticks"], 1)


class Harvest(unittest.TestCase):
    PRD_EXAMPLE = {"player": {"pos": [20, 0], "heading_deg": 0}, "hold": ["ca_loc", "bong_sung"],
                   "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [22, 0]}],
                   "fish": [], "random_fish": False, "time_left_ticks": 120}

    def test_hai_dung_mep_ban_kinh(self):
        rows, _ = run_gather(self.PRD_EXAMPLE, fr=({"tick": 0, "interact": True},), ticks=1)
        ev = events(rows, "gather")
        self.assertEqual([(e["tick"], e["data"]) for e in ev],
                         [(1, {"node_id": "N1", "kind": "bong_dien_dien", "amount": 1})])
        s = snap_at(rows, 1)
        self.assertEqual(s["hold"], ["ca_loc", "bong_sung", "bong_dien_dien"])
        self.assertEqual(s["nodes"][0]["regrow_ticks"], int(tuning()["regrow_s"] * 60))
        self.assertFalse(s["nodes"][0]["ready"])

    def test_nut_chua_moc_khong_hai_lai(self):
        rows, _ = run_gather(self.PRD_EXAMPLE, fr=({"tick": 0, "interact": True}, {"tick": 1, "interact": False},
                                                   {"tick": 2, "interact": True}), ticks=3)
        self.assertEqual(len(events(rows, "gather")), 1)

    def test_node_regrown_roi_hai_ngay_cung_buoc(self):
        block = dict(self.PRD_EXAMPLE, nodes=[{"id": "N1", "kind": "bong_dien_dien", "pos": [22, 0], "regrow_ticks": 1}])
        rows, _ = run_gather(block, fr=({"tick": 0, "interact": True},), ticks=1)
        self.assertEqual([e["name"] for e in events(rows)], ["node_regrown", "gather"])

    def test_hai_chon_nut_gan_nhat_hoa_theo_id(self):
        block = dict(self.PRD_EXAMPLE, nodes=[{"id": "N10", "kind": "bong_sung", "pos": [21, 0]},
                                              {"id": "N2", "kind": "bong_dien_dien", "pos": [19, 0]}])
        rows, _ = run_gather(block, fr=({"tick": 0, "interact": True},), ticks=1)
        self.assertEqual(events(rows, "gather")[0]["data"]["node_id"], "N2")

    def test_hold_full_khi_hai(self):
        cap = tuning()["hold_capacity"]
        block = dict(self.PRD_EXAMPLE, hold=["ca_loc"] * cap)
        rows, _ = run_gather(block, fr=({"tick": 0, "interact": True},), ticks=1)
        self.assertEqual(events(rows, "gather"), [])
        self.assertEqual(events(rows, "hold_full")[0]["data"],
                         {"action": "gather", "node_id": "N1", "required": 1, "free": 0})
        self.assertTrue(snap_at(rows, 1)["nodes"][0]["ready"])

    def test_khong_hai_duoi_nuoc(self):
        block = dict(self.PRD_EXAMPLE, player={"pos": [22, 1.5]})
        rows, _ = run_gather(block, fr=({"tick": 0, "interact": True},), ticks=1)
        self.assertEqual(events(rows, "gather"), [])


class Catch(unittest.TestCase):
    def block(self, **kw):
        b = {"player": {"pos": [15, 6]}, "random_fish": False,
             "fish": [{"id": "F1", "kind": "ca_linh", "pos": [15, 5]}, {"id": "F2", "kind": "ca_loc", "pos": [40, 10]}]}
        b.update(kw)
        return b

    def test_bat_dan_gan_nhat(self):
        rows, _ = run_gather(self.block(), fr=({"tick": 0, "catch": True},), ticks=1)
        ev = events(rows, "fish_caught")
        self.assertEqual([(e["tick"], e["data"]) for e in ev], [(1, {"fish_id": "F1", "kind": "ca_linh", "yield": 3})])
        s = snap_at(rows, 1)
        self.assertEqual(s["hold"], ["ca_linh"] * 3)
        self.assertEqual([f["id"] for f in s["fish"]], ["F2"])
        self.assertEqual(s["player"]["catch_cd_ticks"], int(tuning()["catch_cooldown_s"] * 60))

    def test_hold_full_giu_dan_va_khong_thu_dan_khac(self):
        cap = tuning()["hold_capacity"]
        fish = [{"id": "F1", "kind": "ca_linh", "pos": [15, 5]}, {"id": "F2", "kind": "ca_loc", "pos": [15, 7.5]}]
        rows, _ = run_gather(self.block(hold=["ca_loc"] * (cap - 2), fish=fish), fr=({"tick": 0, "catch": True},), ticks=1)
        self.assertEqual(events(rows, "fish_caught"), [])
        self.assertEqual(events(rows, "hold_full")[0]["data"],
                         {"action": "catch", "fish_id": "F1", "required": 3, "free": 2})
        s = snap_at(rows, 1)
        self.assertEqual(len(s["fish"]), 2)
        self.assertEqual(s["player"]["catch_cd_ticks"], 0)

    def test_hoi_chieu_dung_lai_tu_t_cong_L(self):
        fish = [{"id": "F1", "kind": "ca_loc", "pos": [15, 5]}, {"id": "F2", "kind": "ca_loc", "pos": [15, 7]}]
        L = int(tuning()["catch_cooldown_s"] * 60)
        fr = ({"tick": 0, "catch": True}, {"tick": 1, "catch": False}, {"tick": L - 1, "catch": True},
              {"tick": L, "catch": False}, {"tick": L + 1, "catch": True})
        rows, _ = run_gather(self.block(fish=fish), fr=fr, ticks=L + 2)
        # bắt ở tick 1; bấm ở tick L (sớm 1 tick) bị bỏ qua; bấm ở tick L + 2 (>= 1 + L) bắt được
        self.assertEqual([e["tick"] for e in events(rows, "fish_caught")], [1, L + 2])

    def test_hoa_khoang_cach_theo_id(self):
        fish = [{"id": "F10", "kind": "ca_loc", "pos": [16, 6]}, {"id": "F2", "kind": "ca_linh", "pos": [14, 6]}]
        rows, _ = run_gather(self.block(fish=fish), fr=({"tick": 0, "catch": True},), ticks=1)
        self.assertEqual(events(rows, "fish_caught")[0]["data"]["fish_id"], "F2")

    def test_khong_bat_o_mat_nuoc_va_ngoai_tam(self):
        rows, _ = run_gather(self.block(player={"pos": [15, 0]}), fr=({"tick": 0, "catch": True},), ticks=1)
        self.assertEqual(events(rows, "fish_caught"), [])
        rows, _ = run_gather(self.block(player={"pos": [25, 6]}), fr=({"tick": 0, "catch": True},), ticks=1)
        self.assertEqual(events(rows), [])
        self.assertEqual(snap_at(rows, 1)["player"]["catch_cd_ticks"], 0)


class EndOfMorning(unittest.TestCase):
    def test_cap_ben_o_buoc_cuoi_van_docked(self):
        rows, inv = run_gather({"hold": ["ca_loc"], "time_left_ticks": 1, **NO_FISH},
                               fr=({"tick": 0, "interact": True},), ticks=5, inventory_out=True)
        self.assertEqual(events(rows, "gather_end")[0]["data"]["reason"], "docked")
        self.assertEqual(inv, {"items": {"ca_loc": 1}})

    def test_bat_hop_le_o_buoc_cuoi_van_vao_kho(self):
        block = {"player": {"pos": [15, 6]}, "time_left_ticks": 1, "random_fish": False,
                 "fish": [{"id": "F1", "kind": "ca_linh", "pos": [15, 5]}]}
        rows, inv = run_gather(block, fr=({"tick": 0, "catch": True},), ticks=5, inventory_out=True)
        self.assertEqual([e["name"] for e in events(rows)], ["fish_caught", "gather_end"])
        self.assertEqual(events(rows, "gather_end")[0]["data"]["reason"], "time")
        self.assertEqual(inv, {"items": {"ca_linh": 3}})


if __name__ == "__main__":
    unittest.main()

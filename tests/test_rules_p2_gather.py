"""Test luật Gather Phase 2 (TICKET-02 mục 1.1–1.2, Test Contract v1.1), hộp đen qua headless_cmd.

Phủ: số chuẩn, cá bơi/đổi hướng/phản xạ mép, sinh cá theo lịch, Cá Sấu patrol/chase/recoil, hit + LIFO + bất tử,
ngất do quái, thứ tự ngạt trước hit, kiểm fixture `monsters[]`.
Quy ước tick: bước k đọc frame tick k và ghi event ở tick k + 1.
"""

import json
import math
import unittest

from helpers import Workdir, events, kinds_of, read_jsonl, run_headless, write_json
from test_rules_gather import run_gather, snap_at


def tuning():
    with open("game.contract.json", encoding="utf-8") as f:
        return json.load(f)["tuning"]["gather"]


G = tuning()
SP = G["monsters"]["species"]["ca_sau"]
NO_FISH = {"fish": [], "random_fish": False}
NO_MON = {"monsters": []}
FISH_STEP = G["fish_speed"] / 60
# JSONL làm tròn số thực 3 chữ số khi xuất, nên so vị trí với places=2


def exit_code(block):
    with Workdir() as w:
        sc = write_json(w.path("sc.json"), {"gather": block})
        return run_headless("--mode", "gather", "--seed", "1", "--ticks", "0", "--scenario", sc, "--out", w.path("o.jsonl"))[0]


def mon(mid="M1", pos=(50, 20), wps=((50, 20), (54, 20)), **kw):
    return dict({"id": mid, "kind": "ca_sau", "pos": list(pos), "waypoints": [list(p) for p in wps]}, **kw)


class StandardNumbers(unittest.TestCase):
    def test_so_chuan_v11(self):
        with open("game.contract.json", encoding="utf-8") as f:
            c = json.load(f)
        self.assertIn(c["contract_version"], ("1.1", "1.2"))  # số chuẩn v1.1 giữ nguyên ở v1.2
        self.assertEqual(G["fish_yield"], {"ca_linh": 3, "ca_loc": 1, "ca_keo": 2})
        self.assertEqual([(n["id"], n["kind"], n["pos"]) for n in G["nodes"]],
                         [("N1", "bong_dien_dien", [12, 0]), ("N2", "bong_dien_dien", [28, 0]),
                          ("N3", "bong_sung", [44, 0]), ("N4", "bong_sung", [60, 0]),
                          ("N5", "keo_neo", [76, 0]), ("N6", "keo_neo", [90, 0])])
        self.assertEqual((G["fish_initial"], G["fish_max"], G["fish_spawn_ticks"], G["fish_turn_ticks"]), (8, 12, 360, 120))
        self.assertEqual(G["fish_speed"], 1.5)
        self.assertEqual(G["fish_depths"], {"ca_linh": [3, 12], "ca_loc": [8, 20], "ca_keo": [22, 28]})
        self.assertEqual(G["fish_spawn_depths"], {"ca_linh": [5, 10], "ca_loc": [10, 16], "ca_keo": [24, 27]})
        pairs = {(k, x, d) for k, ds in G["fish_spawn_depths"].items() for x in G["fish_spawn_x"] for d in ds}
        self.assertEqual(len(pairs), 36)
        self.assertEqual(len({(x, d) for _, x, d in pairs}), 30)
        self.assertEqual(SP, {"patrol_speed": 1.0, "chase_speed": 3.0, "detect_radius": 10, "exit_radius": 16,
                              "depths": [10, 30], "hit_radius": 1.5, "recoil_ticks": 60, "recoil_dist": 2})
        self.assertEqual((G["monsters"]["invuln_ticks"], G["monsters"]["loss_ratio"]), (90, 0.5))

    def test_ca_keo_cho_2_o_va_hai_keo_neo(self):
        block = {"player": {"pos": [50, 25]}, "random_fish": False, **NO_MON,
                 "fish": [{"id": "F1", "kind": "ca_keo", "pos": [50, 24]}]}
        rows, _ = run_gather(block, fr=({"tick": 0, "catch": True},), ticks=1)
        self.assertEqual(events(rows, "fish_caught")[0]["data"], {"fish_id": "F1", "kind": "ca_keo", "yield": 2})
        rows, _ = run_gather({"player": {"pos": [76, 0]}, **NO_FISH}, fr=({"tick": 0, "interact": True},), ticks=1)
        self.assertEqual(events(rows, "gather")[0]["data"], {"node_id": "N5", "kind": "keo_neo", "amount": 1})


class FishInitialAndSpawn(unittest.TestCase):
    def test_dau_ca_8_dan_o_8_diem_khac_nhau(self):
        for seed in (1, 2, 3):
            with Workdir() as w:
                code, err = run_headless("--mode", "gather", "--seed", str(seed), "--ticks", "0", "--out", w.path("o.jsonl"))
                self.assertEqual(code, 0, err)
                fish = read_jsonl(w.path("o.jsonl"))[0]["fish"]
            self.assertEqual(len(fish), 8)
            self.assertEqual(len({tuple(f["pos"]) for f in fish}), 8)
            for f in fish:
                self.assertIn(f["pos"][0], G["fish_spawn_x"])
                self.assertIn(f["pos"][1], G["fish_spawn_depths"][f["kind"]], f)
                self.assertEqual(f["age_ticks"], 0)

    def test_sinh_moi_360_tick_sau_khi_boi(self):
        rows, _ = run_gather({**NO_MON}, ticks=720)
        sp = events(rows, "fish_spawned")
        self.assertEqual([e["tick"] for e in sp], [360, 720])
        for e in sp:
            d = e["data"]
            self.assertEqual(set(d), {"id", "kind", "pos"})
            self.assertIn(d["pos"][1], G["fish_spawn_depths"][d["kind"]])
            s = snap_at(rows, e["tick"])
            others = [f for f in s["fish"] if f["id"] != d["id"]]
            self.assertTrue(all(math.dist(f["pos"], d["pos"]) > G["fish_spawn_clearance"] for f in others))
            new = [f for f in s["fish"] if f["id"] == d["id"]][0]
            self.assertEqual((new["pos"], new["age_ticks"]), (d["pos"], 0), "cá mới tham gia bơi từ bước sau")
        self.assertEqual([e["data"]["id"] for e in sp], ["F9", "F10"])

    def test_tran_12_dan_thi_khong_sinh(self):
        fish = [{"id": f"F{i}", "kind": "ca_keo", "pos": [10 + 7 * i, 25], "heading_deg": 90} for i in range(1, 12)]
        rows, _ = run_gather({"fish": fish, **NO_MON}, ticks=720)
        self.assertEqual([e["tick"] for e in events(rows, "fish_spawned")], [360])
        self.assertEqual(events(rows, "fish_spawned")[0]["data"]["id"], "F12")
        self.assertEqual(len(snap_at(rows, 720)["fish"]), 12)

    def test_random_fish_false_ca_dung_yen_khong_sinh(self):
        rows, _ = run_gather({"random_fish": False, **NO_MON,
                              "fish": [{"id": "F1", "kind": "ca_linh", "pos": [50, 5]}]}, ticks=400)
        self.assertEqual(events(rows, "fish_spawned"), [])
        self.assertEqual(snap_at(rows, 400)["fish"][0]["pos"], [50, 5])

    def test_cung_seed_giong_tung_byte(self):
        with Workdir() as w:
            for i in (1, 2):
                code, err = run_headless("--mode", "gather", "--seed", "9", "--ticks", "1500", "--out", w.path(f"o{i}.jsonl"))
                self.assertEqual(code, 0, err)
            with open(w.path("o1.jsonl"), "rb") as a, open(w.path("o2.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())


class FishSwim(unittest.TestCase):
    def one(self, f, ticks=1):
        rows, _ = run_gather({"fish": [dict({"id": "F1", "kind": "ca_linh"}, **f)], **NO_MON}, ticks=ticks)
        return rows

    def test_boi_1_5_m_s(self):
        p = snap_at(self.one({"pos": [50, 5], "heading_deg": 0}, ticks=60), 60)["fish"][0]
        self.assertAlmostEqual(p["pos"][0], 51.5, places=2)
        self.assertAlmostEqual(p["pos"][1], 5, places=2)
        self.assertEqual(p["age_ticks"], 60)

    def test_phan_xa_mep_x_va_dao_huong(self):
        f = snap_at(self.one({"pos": [95.99, 5], "heading_deg": 0}), 1)["fish"][0]
        self.assertAlmostEqual(f["pos"][0], 96 - (95.99 + FISH_STEP - 96), places=2)
        self.assertAlmostEqual(f["heading_deg"], 180, places=2)

    def test_phan_xa_mep_d_theo_dai_loai(self):
        f = snap_at(self.one({"pos": [50, 11.99], "heading_deg": 90}), 1)["fish"][0]  # cá linh d ∈ [3, 12]
        self.assertAlmostEqual(f["pos"][1], 12 - (11.99 + FISH_STEP - 12), places=2)
        self.assertAlmostEqual(f["heading_deg"], 270, places=2)

    def test_cham_goc_dao_ca_hai(self):
        f = snap_at(self.one({"pos": [95.99, 11.99], "heading_deg": 45}), 1)["fish"][0]
        self.assertAlmostEqual(f["heading_deg"], 225, places=2)
        self.assertLess(f["pos"][0], 96)
        self.assertLess(f["pos"][1], 12)

    def test_doi_huong_o_buoc_boi_thu_120_truoc_khi_di(self):
        rows = self.one({"pos": [50, 5], "heading_deg": 0, "age_ticks": 118}, ticks=2)
        a, b = snap_at(rows, 1)["fish"][0], snap_at(rows, 2)["fish"][0]
        self.assertEqual(a["heading_deg"], 0, "bước bơi thứ 119 chưa đổi hướng")
        self.assertEqual(b["age_ticks"], 120)
        h = math.radians(b["heading_deg"])
        want = [a["pos"][0] + math.cos(h) * FISH_STEP, a["pos"][1] + math.sin(h) * FISH_STEP]
        if 3 < want[1] < 12:  # không chạm mép: vị trí đi theo hướng MỚI ngay trong bước 120
            self.assertAlmostEqual(b["pos"][0], want[0], places=2)
            self.assertAlmostEqual(b["pos"][1], want[1], places=2)

    def test_bat_theo_vi_tri_ca_truoc_khi_boi(self):
        # đàn đúng mép 2.0 m và đang bơi ra xa: vẫn bắt được vì bắt xét trước khi cá bơi
        block = {"player": {"pos": [15, 5]}, **NO_MON, "fish": [{"id": "F1", "kind": "ca_linh", "pos": [17, 5]}]}
        rows, _ = run_gather(block, fr=({"tick": 0, "catch": True},), ticks=1)
        self.assertEqual(len(events(rows, "fish_caught")), 1)


class Monsters(unittest.TestCase):
    def test_bo_tri_ngay_1_chi_co_M1_va_tuan_tra(self):
        rows, _ = run_gather({**NO_FISH}, ticks=300)
        ms = snap_at(rows, 0)["monsters"]
        self.assertEqual(ms, [{"id": "M1", "kind": "ca_sau", "pos": [60, 24], "waypoints": [[60, 24], [64, 24]],
                               "target_idx": 1, "state": "patrol", "state_ticks_left": 0, "recoil_dir": None}])
        self.assertAlmostEqual(snap_at(rows, 60)["monsters"][0]["pos"][0], 61, places=2)
        m = snap_at(rows, 240)["monsters"][0]
        self.assertAlmostEqual(m["pos"][0], 64, places=2)
        self.assertEqual(m["target_idx"], 0, "đến waypoint thì đổi mục tiêu cho bước sau")
        self.assertLess(snap_at(rows, 300)["monsters"][0]["pos"][0], 64)

    def test_phat_hien_chase_va_boi_3_m_s(self):
        rows, _ = run_gather({"player": {"pos": [60, 15]}, **NO_FISH}, ticks=1)  # cách M1 9 m, d >= 10
        m = snap_at(rows, 1)["monsters"][0]
        self.assertEqual(m["state"], "chase")
        self.assertAlmostEqual(math.dist(m["pos"], [60, 24]), SP["chase_speed"] / 60, places=2)

    def test_nguoi_choi_nong_khong_bi_duoi(self):
        rows, _ = run_gather({"player": {"pos": [60, 9.9]}, "monsters": [mon(pos=(60, 10), wps=((60, 10), (64, 10)))],
                              **NO_FISH}, ticks=5)
        self.assertEqual(snap_at(rows, 5)["monsters"][0]["state"], "patrol")
        self.assertEqual(events(rows, "monster_hit"), [], "người chơi ở d < 10 không bị chạm")

    def test_roi_chase_khi_nguoi_choi_len_nong_hoac_xa(self):
        for player in ([50, 5], [80, 20]):
            rows, _ = run_gather({"player": {"pos": player}, "monsters": [mon(state="chase")], **NO_FISH}, ticks=1)
            self.assertEqual(snap_at(rows, 1)["monsters"][0]["state"], "patrol", player)

    def test_hit_mat_mau_rot_LIFO_bat_tu_recoil(self):
        hold = ["ca_loc", "bong_sung", "ca_linh", "ca_keo", "keo_neo"]
        block = {"player": {"pos": [50, 20.5]}, "hold": hold, "monsters": [mon()], **NO_FISH}
        rows, _ = run_gather(block, ticks=100)
        hits = events(rows, "monster_hit")
        self.assertEqual((hits[0]["tick"], hits[0]["data"]),
                         (1, {"monster_id": "M1", "hp": G["hp_max"] - 1, "pos": [50, 20.5],
                              "lost": [{"id": "I5", "kind": "keo_neo", "fresh": 99.992},      # v1.2: cá thể, LIFO
                                       {"id": "I4", "kind": "ca_keo", "fresh": 99.992}]}))
        s1 = snap_at(rows, 1)
        self.assertEqual(kinds_of(s1["hold"]), hold[:3])
        self.assertEqual(s1["player"]["invuln_ticks"], 90)
        m = s1["monsters"][0]
        self.assertEqual((m["state"], m["state_ticks_left"], m["recoil_dir"]), ("recoil", 60, [0.0, -1.0]))
        m2 = snap_at(rows, 2)["monsters"][0]
        self.assertAlmostEqual(m2["pos"][1], m["pos"][1] - SP["recoil_dist"] / SP["recoil_ticks"], places=2)
        self.assertEqual(m2["state_ticks_left"], 59)
        m61 = snap_at(rows, 61)["monsters"][0]
        self.assertEqual((m61["state"], m61["state_ticks_left"], m61["recoil_dir"]), ("patrol", 0, None))
        self.assertAlmostEqual(m61["pos"][1], m["pos"][1] - SP["recoil_dist"], places=2)
        # quái quay lại đuổi nhưng người chơi còn bất tử: hit kế tiếp đúng lúc hết bất tử (tick 1 + 90)
        self.assertEqual([e["tick"] for e in hits], [1, 91])
        self.assertEqual(kinds_of(hits[1]["data"]["lost"]), ["ca_linh"])

    def test_bat_tu_chan_hit(self):
        block = {"player": {"pos": [50, 20.5], "invuln_ticks": 5}, "monsters": [mon()], **NO_FISH}
        rows, _ = run_gather(block, ticks=6)
        self.assertEqual([e["tick"] for e in events(rows, "monster_hit")], [5])

    def test_toi_da_mot_hit_con_gan_nhat_hoa_theo_id(self):
        ms = [mon("M10", pos=(51, 20), wps=((51, 20), (51, 25))), mon("M2", pos=(49, 20), wps=((49, 20), (49, 25)))]
        rows, _ = run_gather({"player": {"pos": [50, 20]}, "monsters": ms, **NO_FISH}, ticks=1)
        hits = events(rows, "monster_hit")
        self.assertEqual([h["data"]["monster_id"] for h in hits], ["M2"])
        by_id = {m["id"]: m for m in snap_at(rows, 1)["monsters"]}
        self.assertEqual((by_id["M2"]["state"], by_id["M10"]["state"]), ("recoil", "chase"))

    def test_trung_tam_recoil_huong_x_duong(self):
        block = {"player": {"pos": [50, 20]}, "monsters": [mon(state="chase")], **NO_FISH}
        rows, _ = run_gather(block, ticks=1)
        self.assertEqual(snap_at(rows, 1)["monsters"][0]["recoil_dir"], [1.0, 0.0])

    def test_quai_recoil_khong_gay_hit(self):
        m = mon(state="recoil", state_ticks_left=3, recoil_dir=[1, 0])
        rows, _ = run_gather({"player": {"pos": [50, 20.5]}, "monsters": [m], **NO_FISH}, ticks=3)
        self.assertEqual(events(rows, "monster_hit"), [])
        self.assertEqual(snap_at(rows, 3)["monsters"][0]["state"], "patrol")

    def test_ngat_do_quai(self):
        block = {"player": {"pos": [50, 20.5], "hp": 1}, "hold": ["ca_loc", "bong_sung", "ca_linh"],
                 "monsters": [mon()], **NO_FISH}
        rows, inv = run_gather(block, ticks=10, inventory_out=True)
        self.assertEqual([e["name"] for e in events(rows)], ["monster_hit", "faint", "gather_end"])
        self.assertEqual(kinds_of(events(rows, "monster_hit")[0]["data"]["lost"]), ["ca_linh"])
        faint = events(rows, "faint")[0]["data"]
        self.assertEqual((faint["cause"], faint["hp"], [i["id"] for i in faint["lost"]]), ("monster", 0, ["I2", "I1"]))
        self.assertEqual(events(rows, "gather_end")[0]["data"], {"reason": "fainted", "inventory": {"items": []}})
        self.assertEqual(inv, {"items": []})
        self.assertEqual(rows[-1]["ticks"], 1)

    def test_ngat_truoc_hit_cung_tick(self):
        block = {"player": {"pos": [50, 20.5], "hp": 2, "oxygen_ticks": 0, "zero_oxy_ticks": 59},
                 "monsters": [mon()], **NO_FISH}
        rows, _ = run_gather(block, ticks=5)
        self.assertEqual([(e["name"], e["data"].get("hp")) for e in events(rows)],
                         [("choke", 1), ("monster_hit", 0), ("faint", 0), ("gather_end", None)])
        self.assertEqual(events(rows, "faint")[0]["data"]["cause"], "monster")

    def test_cap_ben_van_uu_tien_khi_con_mau(self):
        block = {"player": {"pos": [2, 0]}, **NO_FISH, "monsters": []}
        rows, _ = run_gather(block, fr=({"tick": 0, "interact": True},), ticks=1)
        self.assertEqual(events(rows, "gather_end")[0]["data"]["reason"], "docked")


class MonsterFixtures(unittest.TestCase):
    def test_fixture_sai_tra_ma_2(self):
        bad = [
            [mon(kind="ran")],                                   # loài chưa bật
            [mon(wps=((50, 20),))],                               # thiếu waypoint
            [mon(pos=(50, 5))],                                   # ngoài dải độ sâu loài
            [mon(target_idx=2)],
            [mon(state="stunned", state_ticks_left=5)],           # chỉ có khi bật Lao xua
            [mon(state="recoil", recoil_dir=[1, 0])],             # recoil thiếu timer
            [mon(state="recoil", state_ticks_left=5, recoil_dir=[1, 1])],  # không phải vector đơn vị
            [mon(recoil_dir=[1, 0])],                             # recoil_dir khi không recoil
            [mon(), mon()],                                       # id trùng
            [mon(hp=3)],                                          # trường lạ
        ]
        for ms in bad:
            self.assertEqual(exit_code({"monsters": ms}), 2, ms)
        self.assertEqual(exit_code({"fish": [{"id": "F1", "kind": "ca_keo", "pos": [50, 25], "age_ticks": -1}]}), 2)

    def test_fixture_hop_le(self):
        good = [[], [mon()], [mon(state="recoil", state_ticks_left=5, recoil_dir=[0.6, 0.8], target_idx=0)]]
        for ms in good:
            self.assertEqual(exit_code({"monsters": ms}), 0, ms)


if __name__ == "__main__":
    unittest.main()

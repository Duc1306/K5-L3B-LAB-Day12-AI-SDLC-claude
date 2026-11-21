"""Test chơi liền mạch sáng → tối → sáng (chonoi.ngay_dem): kho đi qua file đúng mục G."""

import json
import os
import tempfile
import time
import unittest
import urllib.request

from chonoi.contract import load_contract
from chonoi.inventory import read_inventory
from chonoi.live import LiveServer
from chonoi.ngay_dem import DayGame


def _wait(cond, timeout=6.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


def _snap(game):
    return json.loads(game.state_json())


def _press(game, button="interact"):
    game.set_input({button: True})
    time.sleep(0.1)
    game.set_input({button: False})


class NgayDemTest(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]
        self.tmp = tempfile.mkdtemp(prefix="test-ngay-dem-")
        self.gather_sc = os.path.join(self.tmp, "g.json")
        with open(self.gather_sc, "w", encoding="utf-8") as f:
            json.dump({"gather": {"hold": ["ca_loc", "bong_sung", "bong_sung"]}}, f)   # giống smoke hộp đen
        self.quan_sc = os.path.join(self.tmp, "q.json")
        with open(self.quan_sc, "w", encoding="utf-8") as f:
            json.dump({"quan": {"time_left_ticks": 20}}, f)                            # ca tối ngắn để test

    def _game(self, **kw):
        g = DayGame(self.tuning, seed=42, pause_s=0.1, workdir=os.path.join(self.tmp, "w"),
                    scenario_paths={"gather": self.gather_sc, "quan": self.quan_sc}, **kw)
        os.makedirs(g.workdir, exist_ok=True)
        g.start()
        self.addCleanup(g.stop)
        return g

    def test_cap_ben_thi_quan_nhan_dung_kho(self):
        g = self._game()
        self.assertEqual(_snap(g)["mode"], "gather")
        _press(g)                                                  # đứng ở bến: E -> docked
        self.assertTrue(_wait(lambda: _snap(g)["mode"] == "quan"), "không chuyển sang quán")
        st = _snap(g)
        kho = read_inventory(g.kho_path(1))
        self.assertEqual(kho, {"bong_sung": 2, "ca_loc": 1})
        self.assertEqual(st["stock"], kho)                         # quán nhận đúng file kho buổi sáng
        self.assertEqual(st["day"]["n"], 1)

    def test_het_ca_toi_sang_ngay_moi_va_lap_lai(self):
        g = self._game()
        _press(g)
        self.assertTrue(_wait(lambda: _snap(g)["mode"] == "quan"))
        self.assertTrue(_wait(lambda: _snap(g)["mode"] == "gather"), "quán xong không sang sáng ngày mới")
        st = _snap(g)
        self.assertEqual(st["day"]["n"], 2)
        self.assertEqual(len(g.history), 1)
        self.assertFalse(os.path.exists(g.kho_path(2)))           # ngày mới chưa có kho tới khi gather_end
        _press(g)                                                  # ngày 2 cũng nối được
        self.assertTrue(_wait(lambda: _snap(g)["mode"] == "quan"))
        self.assertEqual(_snap(g)["stock"], read_inventory(g.kho_path(2)))

    def test_het_so_ngay_thi_dung_o_bang_ket_thuc(self):
        g = self._game(days=1)
        _press(g)
        self.assertTrue(_wait(lambda: _snap(g)["mode"] == "quan"))
        self.assertTrue(_wait(lambda: _snap(g)["finished"]))
        time.sleep(0.4)
        st = _snap(g)
        self.assertEqual((st["mode"], st["day"]["n"], st["day"]["next"]), ("quan", 1, None))

    def test_qua_http_cung_mot_cong(self):
        g = DayGame(self.tuning, seed=1, pause_s=0.1, workdir=os.path.join(self.tmp, "h"),
                    scenario_paths={"gather": self.gather_sc})
        os.makedirs(g.workdir, exist_ok=True)
        server = LiveServer(g, port=0)
        server.start()
        self.addCleanup(server.stop)
        base = f"http://127.0.0.1:{server.port}"
        get = lambda: json.loads(urllib.request.urlopen(base + "/state", timeout=5).read())
        post = lambda body: urllib.request.urlopen(urllib.request.Request(
            base + "/input", data=json.dumps(body).encode(), method="POST", headers={"Content-Type": "application/json"}), timeout=5).read()
        self.assertEqual(get()["mode"], "gather")
        post({"interact": True}); time.sleep(0.1); post({"interact": False})
        self.assertTrue(_wait(lambda: get()["mode"] == "quan"))
        self.assertEqual(get()["stock"], {"bong_sung": 2, "ca_loc": 1})


if __name__ == "__main__":
    unittest.main()

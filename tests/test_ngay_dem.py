"""Test chơi trọn vòng ngày trên trình duyệt (chonoi.ngay_dem): dùng chính chế độ `day` của luật."""

import json
import time
import unittest
import urllib.error
import urllib.request

from chonoi.contract import load_contract
from chonoi.live import LiveServer
from chonoi.ngay_dem import DayLiveGame


def _wait(cond, timeout=6.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


class NgayDemLiveTest(unittest.TestCase):
    def setUp(self):
        tuning = load_contract()["tuning"]
        sc = {"day": {"money": 300, "earned": 300},
              "gather": {"hold": [{"id": f"I{i}", "kind": k, "fresh": 100}               # v1.2: cá thể
                                  for i, k in enumerate(["ca_loc", "bong_sung", "bong_sung"], 1)], "random_fish": False},
              "quan": {"time_left_ticks": 20}}
        self.server = LiveServer(DayLiveGame(tuning, sc, seed=1, days=2), port=0)
        self.server.start()
        self.addCleanup(self.server.stop)
        self.base = f"http://127.0.0.1:{self.server.port}"

    def get(self):
        return json.loads(urllib.request.urlopen(self.base + "/state", timeout=5).read())

    def post(self, body):
        req = urllib.request.Request(self.base + "/input", data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(req, timeout=5).status

    def press(self, name):
        self.post({name: True}); time.sleep(0.08); self.post({name: False})

    def test_vong_ngay_qua_http_shop_va_ngay_ke(self):
        st = self.get()
        self.assertEqual((st["mode"], st["phase"], st["day"]), ("day", "gather", 1))
        self.assertEqual([e["name"] for e in st["events"][:3]], ["day_start", "day_plan", "phase_start"])
        self.press("interact")                                         # đứng ở bến: cập bến
        self.assertTrue(_wait(lambda: self.get()["phase"] == "quan"))
        self.assertEqual(sorted((i["id"], i["kind"]) for i in self.get()["stock"]),
                         [("I1", "ca_loc"), ("I2", "bong_sung"), ("I3", "bong_sung")])
        self.assertTrue(_wait(lambda: self.get()["phase"] == "shop"))
        self.assertEqual(self.post({"buy": "oxygen"}), 200)
        self.assertTrue(_wait(lambda: self.get()["upgrades"] == {"oxygen": 1}))
        self.assertEqual(self.get()["money"], 100)
        self.press("shop_done")
        self.assertTrue(_wait(lambda: self.get()["day"] == 2))
        st = self.get()
        self.assertEqual((st["phase"], st["active_upgrades"], st["player"]["oxygen_max_ticks"]), ("gather", {"oxygen": 1}, 2700))

    def test_pause_dung_dong_ho(self):
        self.press("pause")
        self.assertTrue(_wait(lambda: self.get()["state"] == "paused"))
        t1 = self.get()["time_left_ticks"]
        time.sleep(0.3)
        self.assertEqual(self.get()["time_left_ticks"], t1)
        self.press("pause")
        self.assertTrue(_wait(lambda: self.get()["time_left_ticks"] < t1))

    def test_buy_sai_kieu_bi_tu_choi(self):
        req = urllib.request.Request(self.base + "/input", data=json.dumps({"buy": 3}).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(ctx.exception.code, 400)
        ctx.exception.close()


if __name__ == "__main__":
    unittest.main()

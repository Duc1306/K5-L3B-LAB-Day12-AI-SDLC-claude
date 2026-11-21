"""Mã thoát 1 (lỗi chạy/ghi) theo Test Contract — hộp đen qua headless_cmd.

Mã 2 đã có ca kiểm ở test_smoke_p1; file này bổ sung ca mã 1 còn thiếu (AC-P1-08).
"""

import os
import unittest

from helpers import Workdir, frames, read_jsonl, run_headless, write_json


class ExitCode1(unittest.TestCase):
    def test_out_trong_thu_muc_khong_ton_tai_exit_1(self):
        """Đầu vào hợp lệ nhưng không mở được file --out để ghi → lỗi ghi, mã 1 (không phải 2)."""
        with Workdir() as w:
            out = w.path(os.path.join("khong-co", "o.jsonl"))
            for mode in ("gather", "quan"):
                code, err = run_headless("--mode", mode, "--seed", "1", "--ticks", "10", "--out", out)
                self.assertEqual(code, 1, (mode, err))
                self.assertFalse(os.path.exists(out))

    def test_out_la_thu_muc_exit_1(self):
        with Workdir() as w:
            out = w.path("la-thu-muc")
            os.mkdir(out)
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "0", "--out", out)
            self.assertEqual(code, 1, err)

    def test_inventory_out_khong_ghi_duoc_exit_1(self):
        """Cập bến ở tick 0 → gather_end → ghi kho vào thư mục không tồn tại → mã 1; JSONL vẫn đủ dòng end."""
        with Workdir() as w:
            inp = write_json(w.path("dock.json"), frames({"tick": 0, "interact": True}))
            out = w.path("g.jsonl")
            kho = w.path(os.path.join("khong-co", "kho.json"))
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "60", "--inputs", inp,
                                     "--out", out, "--inventory-out", kho)
            self.assertEqual(code, 1, err)
            self.assertFalse(os.path.exists(kho))
            rows = read_jsonl(out)
            self.assertEqual(rows[-1]["type"], "end")
            self.assertEqual(rows[-1]["reason"], "docked")

    def test_dau_vao_sai_van_uu_tien_exit_2(self):
        """Vừa sai đầu vào vừa không ghi được → kiểm đầu vào TRƯỚC, nên mã 2."""
        with Workdir() as w:
            out = w.path(os.path.join("khong-co", "o.jsonl"))
            code, _ = run_headless("--mode", "gather", "--seed", "1", "--ticks", "-1", "--out", out)
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()

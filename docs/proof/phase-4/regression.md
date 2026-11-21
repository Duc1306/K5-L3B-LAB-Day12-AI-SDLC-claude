# Regression toàn bộ trên `main` (Phase 4) — Shirou191 (QA)

Chạy trên commit `333bb68` (sau `cd8a8de` của hadatttt + các commit skill/hook/hợp đồng của Shirou191), Windows 11, Python 3.14.
Trên Windows, `headless_cmd` gọi `python3`, nên máy cần có lệnh `python3` trên PATH. Tôi dùng một bản sao `python.exe` đặt tên `python3.exe`, chỉ trên máy mình, không commit.

## 1. Toàn bộ test (191 ca, gồm regression P1–P3 và mở rộng Cháy món)

`PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` → **Ran 191 tests, OK**. Log đầy đủ: [unittest.txt](unittest.txt).

## 2. Tất định từng byte (`tools/kiem_tat_dinh.py`, cũng là các bước của hook `pre-push`)

```text
$ python3 tools/kiem_tat_dinh.py --mode gather --seed 1 --ticks 600 --inputs docs/proof/phase-1/g/day-inputs.json
JSONL  lần 1 20a25d9fc80815ca2318e0a54b5780985e5dc44a848a425fdc888bf79827147d
JSONL  lần 2 20a25d9fc80815ca2318e0a54b5780985e5dc44a848a425fdc888bf79827147d
Kho    hai lần 881b0aeb31caa77f0cb608c2c79aa80ac1f0439dcc7387ed10c9c7f0a848f342
TẤT ĐỊNH: OK
$ python3 tools/kiem_tat_dinh.py --mode quan --seed 3 --ticks 3000 --inventory docs/contracts/inventory.sample.json
JSONL  lần 1 a440d1b2bb07ad813a63875afdf53219ef97043d97592645befb1f6b81a2d1bc
JSONL  lần 2 a440d1b2bb07ad813a63875afdf53219ef97043d97592645befb1f6b81a2d1bc
TẤT ĐỊNH: OK
$ python3 tools/kiem_tat_dinh.py --mode day --seed 1 --days 2 --ticks 44400
JSONL  lần 1 9e78c97b4f782a07bc6e2ab59b752164c2385b09cb9633652981eae76198fe45
JSONL  lần 2 9e78c97b4f782a07bc6e2ab59b752164c2385b09cb9633652981eae76198fe45
TẤT ĐỊNH: OK
```

## 3. Smoke 2 tiến trình qua file kho v1.2 (cá thể)

Giỏ mẫu gồm 3 cá thể (`I1`, `I2` bông súng, `I3` cá lóc), cập bến ở tick 0:

```bash
python3 -m chonoi.headless --mode gather --seed 1 --ticks 600 --scenario dock.json --inputs dock-in.json --out g.jsonl --inventory-out kho.json   # mã 0
python3 -m chonoi.headless --mode quan --seed 1 --ticks 60 --inventory kho.json --out q.jsonl                                          # mã 0
```

- `kho.json`: `{"items":[{"id":"I1","kind":"bong_sung","fresh":99.99166666666666},{"id":"I2","kind":"bong_sung","fresh":99.99166666666666},{"id":"I3","kind":"ca_loc","fresh":99.99166666666666}]}`
- Snapshot quán tick 0 có `stock` gồm đúng 3 cá thể `I1`, `I2`, `I3`, cùng kind. `fresh` 99.992 là giá trị đã làm tròn 3 chữ số khi xuất JSONL. Số này khớp với file kho: hàng hao 2/240 điểm trong bước cập bến.

## 4. Hiệu năng `day`

`python3 -m chonoi.headless --mode day --seed 7 --days 5 --ticks 200000` → **2,8 s** cho 5 Ngày (111.000 tick). Đề yêu cầu một Ngày ≤ 20 s.
Dòng end: `{"reason":"days_complete","days_completed":5,"ticks":111000,"score":300}`.

## Kết luận
Không có regression ở `main`. Cả 3 mode chạy tất định. Bàn giao kho v1.2 giữ nguyên id, kind và độ tươi. Hiệu năng `day` dư xa so với ngưỡng 20 s.

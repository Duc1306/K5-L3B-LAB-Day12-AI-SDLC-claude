# Kiểm chứng chế độ day / Shop / pause (Phase 2, chạy thật)

## 1. `day --days 1` (không input, không pause)
- exit 0, chạy 1.17 s (yêu cầu ≤ 20 s) · 3 event đầu: [(0, 'gather', 1, 'day_start'), (0, 'gather', 1, 'day_plan'), (0, 'gather', 1, 'phase_start')]
- `day_plan` D1: `{"dishes": {"ca_loc_nuong_trui": 3, "goi_bong_sung": 3}, "ingredients": {"bong_sung": 6, "ca_loc": 3}}`
- `phase_start`: [(0, 'gather'), (10800, 'quan'), (21600, 'shop')] · `shop_end`: {'reason': 'time'}
- end: `{"type": "end", "ticks": 22200, "sim_tick": 22200, "mode": "day", "state": "finished", "reason": "days_complete", "money": 0, "earned": 0, "reputation": 3.0, "score": 300, "days_completed": 1}`
- **ĐẠT: True** (một Ngày không pause = 10800 + 10800 + 600 = 22200 tick)

## 2. `day --days 5`: kế hoạch D1–D5 và Cá Sấu theo Ngày
- exit 0, 3.54 s · end: ticks 111000, reason days_complete, days_completed 5
- `day_plan` từng Ngày khớp `tuning.day_plan`: True
- Quái ở đầu mỗi Ngày: {1: ['M1'], 2: ['M1'], 3: ['M1', 'M2'], 4: ['M1', 'M2'], 5: ['M1', 'M2']}
- **ĐẠT: True**

## 3. Shop và nâng cấp (2 Ngày)
- tick 22 `bought` {"upgrade": "oxygen", "level": 1, "price": 200, "money": 500}
- tick 23 `bought` {"upgrade": "hp", "level": 1, "price": 250, "money": 250}
- tick 24 `buy_failed` {"action": "hp", "reason": "funds"}
- tick 25 `buy_failed` {"action": "weapon", "reason": "unknown"}
- tick 48 `buy_failed` {"action": "oxygen", "reason": "funds"}
- Shop Ngày 1 (tick 25): upgrades {'hp': 1, 'oxygen': 1}, active {}, money 250, earned 700
- Ngày 2 (tick 26): active {'hp': 1, 'oxygen': 1}, oxygen_max_ticks 2700, hp_max 4, hp 4
- end: {"type": "end", "ticks": 49, "sim_tick": 49, "mode": "day", "state": "finished", "reason": "days_complete", "money": 250, "earned": 700, "reputation": 3.0, "score": 1000, "days_completed": 2}
- **ĐẠT: True** (cấp hiện ngay ở `upgrades`, áp dụng từ Ngày kế; trừ `money`, giữ `earned`)

## 4. Pause trong `day`
- event: [(6, 'paused'), (51, 'resumed')] · snapshot tick 30: state paused, sim_tick 5, phase_tick 5, time_left 10795
- end: ticks 100, sim_tick 55
- **ĐẠT: True** (pause 45 bước ngoài: sim_tick/phase_tick/đồng hồ đứng yên)

## 5. Tất định từng byte (chạy 2 lần)
- gather: 4a9569e05472ec7b = 4a9569e05472ec7b → True
- quan: 2bb0085bf491c110 = 2bb0085bf491c110 → True
- day: 0426f66831817ae7 = 0426f66831817ae7 → True
- **ĐẠT: True**

## 6. Mã thoát 2 với cờ/scenario sai
- --days 6: exit 2 (đầu vào sai: --days phải là số nguyên từ 1 đến 5)
- --days với gather: exit 2 (đầu vào sai: --days chỉ dùng với --mode day)
- --inventory với day: exit 2 (đầu vào sai: --inventory / --inventory-out dành cho hai mode độc lập, )
- quan.stock trong day: exit 2 (đầu vào sai: --mode day cấm quan.stock (dùng gather.hold / day.reputat)
- **ĐẠT: True**

> JSONL lớn không commit (tạo lại bằng các lệnh trên): `d/day1.jsonl` (~3.3 MB), `d/det-gather-*.jsonl`, `d/det-quan-*.jsonl`. Các JSONL nhỏ được commit bằng `git add -f` vì `.gitignore` bỏ `*.jsonl`.

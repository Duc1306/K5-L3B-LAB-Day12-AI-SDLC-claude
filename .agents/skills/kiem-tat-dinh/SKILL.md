---
name: kiem-tat-dinh
description: Kiểm game Chợ Nổi còn tất định và đúng Test Contract sau khi sửa luật (chonoi/sim/*, runner, rng, scenario, inventory) hoặc trước khi gắn tag phase. Chạy headless 2 lần cùng seed/đầu vào, so JSONL và file kho từng byte, rồi chạy toàn bộ test. Dùng khi được yêu cầu "kiểm tất định", "so JSONL 2 lần", "kiểm trước khi tag/push", hoặc khi nghi có random toàn cục / đồng hồ hệ thống lọt vào sim.
---

# Skill: Kiểm tất định + Test Contract

Test ẩn của giảng viên so JSONL **từng byte** giữa các lần chạy cùng seed. Chỉ một lần gọi
`random.random()` toàn cục, một `time.time()` hay duyệt `set`/`dict` không sắp xếp là mất điểm cả phase,
kể cả khi luật đúng. Skill này giúp bắt lỗi đó trước khi push.

## 1. Khi nào chạy
- Sau mọi thay đổi trong `chonoi/sim/*`, `chonoi/runner.py`, `chonoi/rng.py`, `chonoi/scenario.py`, `chonoi/inventory.py`.
- Trước khi gắn tag `phase-n` (test ẩn kiểm lại cả phase trước).
- **Không cần** khi chỉ sửa `chonoi/web/` (đồ họa chỉ đọc snapshot, xem skill `thiet-ke-do-hoa`).

## 2. Các bước
1. Chạy toàn bộ test (phải xanh trước khi làm tiếp):
   `PYTHONPATH=tests:. python3 -m unittest discover -s tests`
2. Kiểm tất định cho cả hai buổi, có đầu vào thật (input rỗng thì nhiều nhánh luật không chạy tới):
   ```bash
   python3 tools/kiem_tat_dinh.py --mode gather --seed 1 --ticks 600 --inputs docs/proof/phase-1/g/day-inputs.json
   python3 tools/kiem_tat_dinh.py --mode quan   --seed 3 --ticks 3000 --inventory docs/proof/phase-1/g/day-kho.json
   ```
   Có `--mode day` (Phase 2+) thì chạy thêm `--mode day`.
3. Đổi seed (ví dụ 1, 7, 42) để thấy RNG thật sự đi qua `Streams`: cùng seed phải trùng, khác seed nên khác
   ở phần có ngẫu nhiên (cá, khách).
4. Ghi kết quả (lệnh + hash + "TẤT ĐỊNH: OK") vào mô tả commit hoặc `docs/proof/phase-n/`.

## 3. Đọc kết quả `tools/kiem_tat_dinh.py`
- Mã thoát `0` → trùng khớp. `1` → lệch: script in **dòng JSONL khác đầu tiên** của hai lần. `2` → headless báo lỗi (đọc stderr).
- Script chạy qua `headless_cmd` của `game.contract.json`, ghi vào thư mục tạm, **không** sửa repo.

## 4. Lệch thì tìm ở đâu
| Triệu chứng | Nguyên nhân thường gặp | Sửa |
|---|---|---|
| Lệch ngay từ snapshot tick 0 | duyệt `set`/`dict` khi dựng fixture | sắp bằng `ids.sort_by_id` / `sorted()` |
| Lệch ở event khách / cá | `import random` toàn cục, `random.choice` | dùng luồng riêng trong `Streams` (`chonoi/rng.py`) |
| Lệch ngẫu nhiên giữa các máy | `time.time()`, `datetime.now()`, `id()`, `hash()` của chuỗi | bỏ; mọi thời gian tính theo tick |
| Tọa độ lệch chữ số cuối | làm tròn trong luật thay vì lúc xuất | tính bằng giá trị chính xác, chỉ `jsonl.py` làm tròn |
| File kho lệch | ghi thứ tự khóa không sắp xếp | dùng `inventory.write_inventory` |

## 5. Không được làm
- Không sửa test hay nới so sánh cho "xanh"; sửa luật (xem `AGENTS.md`).
- Không đổi `game.contract.json` / `docs/contracts/` để che lệch.

## 6. Hook đi kèm
`.githooks/pre-push` chạy bước 1 và bước 2 tự động. Bật một lần cho mỗi máy:
`git config core.hooksPath .githooks`. Bỏ qua khi khẩn cấp: `git push --no-verify` (ghi lý do trong standup).

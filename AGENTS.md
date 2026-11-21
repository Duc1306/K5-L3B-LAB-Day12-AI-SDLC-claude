# AGENTS.md — hướng dẫn chung cho mọi agent AI của nhóm

> Cập nhật file này qua các phase (lịch sử git phải cho thấy điều đó). Ngắn gọn, có lệnh chạy thật.

## Lệnh
- Test: `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`
- Headless: `python3 -m chonoi.headless --mode gather|quan --seed 1 --ticks 600 --out out.jsonl`
- Headless cả vòng ngày (v1.1): `python3 -m chonoi.headless --mode day --seed 1 --days 2 --ticks 44400 --out day.jsonl` (một Ngày không pause = 22.200 tick). Luật ở `chonoi/sim/day.py` + `chonoi/sim/shop.py`; pause xử lý chung trong `runner.Session`.
- Khung đã sửa ở P2 (lý do: Test Contract v1.1): `runner.py` (pause, `sim_tick`/`phase_tick` thật, event `day`, `days_completed`), `headless.py` (`--days`, cho phép `day`), `inputs.py` (`pause`, `shop_done`, `attack`, `photo`, `buy`), `scenario.py` (khối `day`).
- Chơi thử trên trình duyệt: `python3 -m chonoi.live --mode gather|quan` (mở địa chỉ in ra; WASD, E, Space, R, H nhật ký)
- Chơi liền mạch sáng → tối → sáng ngày mới… (một tiến trình, kho qua file đúng mục G; chưa phải `--mode day` của Phase 2): `python3 -m chonoi.ngay_dem [--so-ngay N] [--nghi 4] [--port 8000]`
- Windows: đặt `PYTHONIOENCODING=utf-8` trước khi chạy live, nếu không máy chủ lỗi khi in tiếng Việt.

## Cấu trúc & quy ước
- (Starter Python là TÙY CHỌN; nhóm có thể dùng ngôn ngữ khác nếu giữ Test Contract.) Khung do giảng viên cấp: `chonoi/{headless,inputs,scenario,contract,rng,ids,jsonl,inventory,runner,live}.py` và `chonoi/web/`. Hạn chế sửa; nếu phải sửa thì báo cả nhóm và ghi lại lý do.
- Luật chơi của nhóm: `chonoi/sim/gather.py`, `chonoi/sim/quan.py` (tìm `TODO(nhóm)`).
- **Số liệu chỉ đọc từ `game.contract.json` / dữ liệu**, không hard-code trong luật.
- Mọi số ngẫu nhiên đi qua `Streams` (`chonoi/rng.py`); không dùng `random` toàn cục, không dùng đồng hồ hệ thống.
- Sắp danh sách thực thể bằng `ids.sort_by_id`; cấp id bằng `IdAllocator`.

## Nên tránh
- Không sửa `docs/contracts/`, `game.contract.json` (khóa contract) hoặc schema kho khi chưa báo cả nhóm (đổi hợp đồng ảnh hưởng mọi module).
- Không làm hỏng nhánh chính: trước khi đẩy, chạy test.
- Không bịa yêu cầu: chỗ mơ hồ thì ghi `docs/clarify.md` và hỏi PO.
- Không sửa test cho xanh khi luật sai; phải sửa luật hoặc ghi lý do đổi test trong commit.

## Quy tắc làm việc với agent
- Mỗi agent một việc rõ ràng (một lát). Cho agent đọc PRD/ticket đúng phase và hợp đồng kho trước.
- Agent làm xong phải chạy test và ghi kết quả vào mô tả commit hoặc `docs/proof/`; người đọc lại thay đổi trước khi đẩy.
- Sáng tạo thêm được khuyến khích nhưng phải tắt ở headless (xem README, mục "Tự do sáng tạo").

## Skills / hooks của nhóm
- (Ghi tên và khi nào dùng; tối thiểu 2 skill/hook/command nhóm tự viết, đặt ở `.agents/skills/` hoặc tương đương.)
- `thiet-ke-do-hoa` (`.agents/skills/thiet-ke-do-hoa/SKILL.md`): dùng khi vẽ/animation/thoại cho `chonoi/web/index.html` (cảnh lặn nhìn ngang, nhà bè nhìn từ trên xuống, Út Sen, ánh sáng sáng/tối) hoặc thêm asset ngoài và ghi `CREDITS.md`. Chỉ đọc snapshot, không đụng sim/headless/contract.
- `kiem-tat-dinh` (`.agents/skills/kiem-tat-dinh/SKILL.md` + `tools/kiem_tat_dinh.py`): dùng sau mọi thay đổi ở `chonoi/sim/*`, runner, rng, scenario, inventory hoặc trước khi gắn tag. Script chạy headless 2 lần cùng seed, so JSONL và file kho từng byte, lệch thì in dòng khác đầu tiên. Lệnh: `python3 tools/kiem_tat_dinh.py --mode gather --seed 1 --ticks 600 --inputs docs/proof/phase-1/g/day-inputs.json`.
- Hook `.githooks/pre-push`: trước khi push, chạy toàn bộ test và kiểm tất định cả gather lẫn quán; đỏ thì chặn push. Bật một lần mỗi máy: `git config core.hooksPath .githooks`.
- Hợp đồng kho, snapshot UI và sự kiện: `docs/contracts/README.md` (đọc trước khi sửa sim hay UI).

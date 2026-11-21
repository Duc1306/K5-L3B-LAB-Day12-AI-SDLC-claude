# Phân công công việc toàn bài lab (nhóm 3 người)

> Áp dụng cho cả 4 phase. Phase 2–4 mới là khung, sẽ cập nhật khi đề từng phase mở trên lab board.
> Đề gợi ý 4–6 người với 4 module (`sim/gather`, `sim/quan`, `client/ui`, `qa`); nhóm 3 người nên mỗi người kiêm nhiều vai.

## Vai và module

| | **A — Gather** | **B — Quán** | **C — UI + QA + Integrator** |
|---|---|---|---|
| Module chính | `chonoi/sim/gather.py`: oxy, ngạt, Máu, ngất, hái nút, bắt cá, giỏ LIFO, sự kiện `gather*`, ghi kho khi `gather_end` | `chonoi/sim/quan.py`: khách theo lịch, giữ chỗ, bếp, bưng, phục vụ, tiền, uy tín; kiểm mâu thuẫn trong `chonoi/scenario.py` | `client/ui` (HUD, đồ họa, phần sáng tạo, phải tắt ở headless), viết test, chạy test đầu cuối |
| Vai quy trình | **PO**: giữ `docs/clarify.md`, hỏi giảng viên | **Scrum/Release**: `docs/standup.md`, `docs/retro.md`, Release `v1.0.0` | **Integrator + QA lead**: giữ `docs/contracts/`, `game.contract.json`, gắn tag `phase-n` |
| Dự phòng cho | B | C | A |

## Việc chung của cả ba người

- Mỗi người ít nhất **3 commit có nội dung**, dùng tài khoản GitHub của mình (làm cặp thì ghi `Co-authored-by:`).
- Mỗi người tự viết `docs/members/<handle>.md`.
- Mỗi người ghi phần mình dùng AI vào `docs/ai-usage-log.md`.
- Mỗi người viết 1 skill/hook trong `.agents/skills/` (cần tối thiểu 2), ví dụ:
  - A: skill "chạy headless rồi so JSONL giữa 2 lần cùng seed"
  - C: hook "chạy test trước khi push"
- Trước khi push phải chạy: `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`

## Kickoff, 15 phút đầu (cả nhóm)

1. Điền `TEAM.md` và đổi `team_size` thành `3` trong `game.contract.json`.
2. Chốt hợp đồng tích hợp ở `docs/contracts/README.md`:
   - schema kho (A và B cùng chốt, vì gather ghi kho còn quán đọc kho)
   - danh sách sự kiện
   - các trường snapshot mà UI được đọc (C chốt)
3. Thống nhất cách dùng Git. Gợi ý: mỗi người một nhánh ngắn, C gộp vào `main` và gắn tag.

## Theo từng phase

| Phase | A | B | C |
|---|---|---|---|
| **1** (0:00–1:00) | Viết luật gather theo PRD-0 | Viết luật quán theo PRD-0, đọc kho mẫu `inventory.sample.json` | Viết test luật cho cả hai sim, ráp gather → kho → quán, viết `docs/verification/phase-1.md`, gắn tag `phase-1` |
| **2** (1:00–1:55) | Phần thay đổi của gather | Phần thay đổi của quán | Cập nhật hợp đồng/ADR khi đổi yêu cầu, chạy lại test phase 1 (test ẩn có kiểm lại phase trước), gắn tag `phase-2` |
| **3** (1:55–2:30) | Chế độ `day` (ghép gather + quán) nếu đề yêu cầu, làm cùng B | Làm cùng A | Bắt đầu UI/HUD thật và phần sáng tạo, gắn tag `phase-3` |
| **4** (2:30–3:00) | Sửa lỗi, viết bằng chứng | Viết retro, tạo Release `v1.0.0` | Chuẩn bị demo, ghi mục "Sáng tạo của nhóm" trong README, gắn tag `phase-4` |

Mỗi phase đều phải có `docs/verification/phase-n.md`. Hết giờ thì gắn tag rồi đi tiếp, chỗ chưa xong ghi trung thực.

## Cần chú ý

- A và B làm hai file khác nhau nên ít bị conflict.
- Chỗ dễ vỡ nhất là schema kho, nên C cần khóa nó sớm. Muốn đổi thì báo cả nhóm và ghi ADR.
- Nếu một mảng xong trước, người đó sang viết test cho mảng còn lại.
- Số liệu chỉ đọc từ `game.contract.json`; ngẫu nhiên chỉ qua `Streams` (xem `AGENTS.md`).

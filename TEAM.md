# TEAM

**Tên nhóm:** claude  **Số người:** 5  (khớp `team_size` trong `game.contract.json`)

| Thành viên | GitHub handle | Module chính | Vai quy trình | Người dự phòng cho |
|---|---|---|---|---|
| Trịnh Minh Đức (2A202604078) | Duc1306 | `sim/gather` + `sim/quan` (luật P1–P3), contract v1.2–v1.3, `bench`/`soak` P4 | Integrator kiêm Release cho P3–P4 (gắn `phase-3`, `phase-4`, `v1.0.0`) | TADIZB |
| | TADIZB | `sim/quan` (cặp với Duc1306), đồ họa gather | Dev cặp với Duc1306 (ghi `Co-authored-by`), đọc lại luật trước khi push | Duc1306 |
| | congvt | `client/ui` + `sim/day` | QA lead (verification P1–P3) | Shirou191 |
| | Shirou191 | `qa` (test mã thoát, hook pre-push, kiểm tất định) + `docs/contracts` | Integrator | congvt |
| Hà Văn Khánh Đạt (2A202604074) | hadatttt | `sim/quan` mở rộng Cháy món (`burn`: `contract.py`, `quan.py`, `test_ext_burn.py`, UI `dish_burnt`) + Release, tài liệu (TEAM, retro, CHANGELOG) | PO + Scrum/Release | Shirou191 |

**Vai quy trình:** PO (đầu mối hỏi giảng viên, giữ `docs/clarify.md`) · Integrator (giữ `docs/contracts/`, gắn tag) · QA lead · Scrum/Release. Có thể kiêm.

## Thỏa thuận làm việc nhóm (≤ 10 dòng)

> **Nháp theo cách nhóm đã làm thực tế. Chờ cả nhóm xác nhận.** Ai đồng ý thì ghi handle vào dòng "Đã xác nhận".

- Kênh liên lạc: … *(nhóm điền: Zalo/Messenger/Discord…)*
- Khi bất đồng về thiết kế hay chỗ đề mơ hồ: ghi vào `docs/clarify.md` (PO hỏi Anh Năm/giảng viên). Chưa có trả lời thì chốt một giả định và ghi người quyết. Thay đổi lớn ghi ADR (vd. `docs/adr/0001-kho-ca-the-v12.md`).
- Khi ai đó trễ hoặc vướng quá 10 phút: báo ngay trong nhóm, người dự phòng (cột cuối bảng trên) nhận việc.
- Standup: phút 20 của mỗi phase theo lịch đề, mỗi người một dòng trong `docs/standup.md`.
- Cách đọc code của nhau:
  - Làm cặp (Duc1306 + TADIZB) thì ghi `Co-authored-by:`.
  - Ai gỡ conflict hoặc tích hợp thì đọc lại phần của người kia và chạy toàn bộ test trước khi push.
- Cách làm việc với Git:
  - Push thẳng `main`. Luôn `git fetch`/`pull` trước khi bắt đầu việc.
  - Rebase thay vì tạo merge commit.
  - Bật hook `git config core.hooksPath .githooks`: chạy test và kiểm tất định trước khi push.
  - Tag `phase-n` do người bàn giao cuối phase gắn sau khi test xanh: congvt gắn `phase-1`, `phase-2`; Duc1306 gắn `phase-3`, `phase-4`, `v1.0.0`.
  - Integrator (Shirou191) giữ `docs/contracts/`.

Đã xác nhận: …

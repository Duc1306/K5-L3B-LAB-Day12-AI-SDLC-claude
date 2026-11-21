# Retro nhóm

## Phase 2 (nhanh)
- Điều tốt: 4 lát tích hợp xong trên `main`. Duc1306 làm lát 1–3 (số chuẩn, cá, Cá Sấu, quán 2 bếp/4 bàn) và chừa sẵn API (`GatherSim(day=, hp_max=, oxygen_max_s=)`, `QuanSim(plan_dishes=)`), nên lát 4 (`day`, Shop, pause) nối vào không phải sửa luật. Hook pre-push và `tools/kiem_tat_dinh.py` của Shirou191 bắt được lệch tất định trước khi đẩy. *(congvt ghi)*
- Điều tệ: nhiều người push thẳng `main` cùng lúc nên congvt phải rebase 3 lần trong một lần đẩy. Script ghi file trên Windows đổi LF → CRLF làm conflict trùm cả file. `TEAM.md` vẫn trống. *(congvt ghi)*
- 1 hành động cho Phase 3: thêm `.gitattributes` (`* text=auto eol=lf`) và điền `TEAM.md` trước khi code. Người nhận: congvt (gitattributes), cả nhóm (TEAM.md). *(đề xuất của congvt, cần nhóm xác nhận)*

## Phase 3 (nhanh) — đổi kho
- Điều tốt: đổi schema theo thứ tự adapter → gather → quán → `day` → test → HUD, bật v1.2 ở cả hai đầu bàn giao trong cùng commit nên `main` không có lúc nửa vời. Helper `as_items`/`counts` giúp chuyển ~60 test cũ mà không phải viết lại ý nghĩa test. *(Duc1306 ghi)*
- Điều rút ra từ lần đổi kho: những chỗ "ngoài code luật" cũng phụ thuộc schema (hook `pre-push`, kho mẫu, HUD, bằng chứng Phase 1). Lần đổi schema sau phải `grep` cả `.githooks/`, `docs/contracts/`, `tools/` chứ không chỉ `chonoi/sim/`. *(Duc1306 ghi)*
- 1 hành động cho Phase 4: điền `TEAM.md` và bật `git config core.hooksPath .githooks` trên máy mọi người. Người nhận: cả nhóm. *(đề xuất, cần nhóm xác nhận)*

## Phase 4 (cuối) — tổng kết
**Rà lại hành động đã chốt ở P2** (*Duc1306 ghi, cần nhóm bổ sung*):
- `.gitattributes` (`* text=auto eol=lf`), người nhận congvt: **chưa làm**. Không có commit nào tạo file này. Cảnh báo LF → CRLF vẫn hiện ở mọi lần commit trên Windows. Lý do: P3 và P4 đều đổi yêu cầu lớn nên việc hạ tầng bị đẩy lùi.
- Điền `TEAM.md`, người nhận cả nhóm: **làm muộn ở P4**. hadatttt điền 5 người theo `git log`, `team_size` 5 (`2576784`). Trễ vì không ai nhận đích danh; đây là rủi ro lớn nhất cả buổi, vì commit của người ngoài `TEAM.md` không được tính.
- Hành động P3 (bật `core.hooksPath` trên máy mọi người): hook chạy được (`bash .githooks/pre-push` OK), nhưng chưa xác nhận từng máy đã bật.

**Điều tốt**
- Thứ tự tích hợp được ghi trước rồi làm theo (ADR-0001 ở P3), nên `main` chạy được ở mọi tag. Regression P1–P3 giữ được qua hai lần đổi hợp đồng: 170 test.
- Đo trước khi tối ưu (profile + tắt từng phần) tránh được việc sửa mù. Mọi số trong README/release lấy từ file trong `docs/proof/`.

**Điều cần sửa**
- Phần việc lệch về một hai người ở P1–P3. TADIZB chỉ có 1 commit đứng tên; đóng góp pair chỉ thấy qua `Co-authored-by`. Ở P4, Shirou191 và hadatttt đã có nhiều commit riêng (hook, regression, Cháy món, TEAM).
- Nhiều người push thẳng `main` cùng lúc. Ở P3 có lần phải stash/pull giữa chừng vì commit đồ họa của TADIZB.

**Số liệu** (`git shortlog -sn`, không tính tác giả starter):
- Xem `git shortlog -sn` trên commit bàn giao. Shirou191 và hadatttt tăng nhiều ở P4.
- Co-author: TADIZB ở mọi commit P1–P4 của Duc1306; hadatttt và Shirou191 ở `2a99be8`.
- Token theo người: không đo được (xem `docs/ai-usage-log.md`).

**Một lỗi AI và cách nhóm xác minh**
- Ở P3, AI để adapter test tự đổi kho đếm sang cá thể. Vì vậy ca "file kho đếm phải trả mã 2" lại chạy với kho hợp lệ và luôn xanh, không kiểm được gì.
- Nhóm phát hiện khi đọc lại test có tên "kho đếm cũ" mà không thấy fixture thô. Cách xác minh: viết hàm chạy fixture thô riêng và chạy CLI thật với `{"items":{"ca_loc":1}}` → mã 2 (`docs/proof/phase-3/checks.md` #4).

**Nếu làm lại**
- Điền `TEAM.md` và bật hook ngay phút đầu.
- Chia lát theo người ngay từ P2, mỗi người tự commit lát của mình.
- Đo bench sớm từ P2 để đồ họa không vượt ngân sách khung hình.

**Hành động tiếp theo**
- congvt và TADIZB viết `docs/members/<handle>.md` (đã có Duc1306, Shirou191, hadatttt). Người nhận: từng người.
- Điền tên thật / vai quy trình còn trống trong `TEAM.md`. Người nhận: hadatttt (PO).
- Thêm `.gitattributes`. Người nhận: congvt.
- Cache lớp nền và cây theo pha để cảnh lặn đạt 60 FPS. Người nhận: người làm đồ họa (congvt/TADIZB).

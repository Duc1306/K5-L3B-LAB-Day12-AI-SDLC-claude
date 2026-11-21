# Retro nhóm

## Phase 2 (nhanh)
- Điều tốt: 4 lát tích hợp xong trên `main`. Duc1306 làm lát 1–3 (số chuẩn, cá, Cá Sấu, quán 2 bếp/4 bàn) và chừa sẵn API (`GatherSim(day=, hp_max=, oxygen_max_s=)`, `QuanSim(plan_dishes=)`), nên lát 4 (`day`, Shop, pause) nối vào không phải sửa luật. Hook pre-push và `tools/kiem_tat_dinh.py` của Shirou191 bắt được lệch tất định trước khi đẩy. *(congvt ghi)*
- Điều tệ: nhiều người push thẳng `main` cùng lúc nên congvt phải rebase 3 lần trong một lần đẩy. Script ghi file trên Windows đổi LF → CRLF làm conflict trùm cả file. `TEAM.md` vẫn trống. *(congvt ghi)*
- 1 hành động cho Phase 3: thêm `.gitattributes` (`* text=auto eol=lf`) và điền `TEAM.md` trước khi code. Người nhận: congvt (gitattributes), cả nhóm (TEAM.md). *(đề xuất của congvt, cần nhóm xác nhận)*

## Phase 4 (cuối)
- Rà lại hành động Phase 2: đã làm chưa? vì sao?
- Điều tốt / điều tệ:
- Số liệu: số commit theo người, cách đọc code của nhau, token theo người:
- Một lần AI sai và cách nhóm phát hiện:
- Nếu làm lại, đổi gì:

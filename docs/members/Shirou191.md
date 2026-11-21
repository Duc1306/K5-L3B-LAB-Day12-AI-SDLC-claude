# Shirou191 — phản tư cá nhân (≤ 200 từ)

Vai: QA + Integrator (`docs/contracts`, hook, kiểm tất định).

- Tôi đã làm (kèm link commit):
  - `241a4ce`: test mã thoát 1, skill `kiem-tat-dinh` + `tools/kiem_tat_dinh.py`, hook `pre-push`, hợp đồng tích hợp v1.0, README phần điều khiển và cách tính điểm.
  - `c2baedd`: `--mode day` bản riêng. Merge `8dd859b` lấy bản của congvt (Phase 3 xây trên đó) và giữ `tests/test_day_mode.py` (19 ca) để kiểm chéo.
  - `eb98b7e`, `70cbf0b`, `0490373`, `f97a147`: sửa skill sau v1.2, hợp đồng mục 3b khớp code, hook kiểm thêm `day`.
- Tôi đã review (kèm link): `sim/day.py` của congvt (`e7f27d7`) khi gỡ conflict: chạy 19 test của tôi lên bản đó, tất cả đều pass sau khi đổi fixture sang v1.2.
- AI sai ở đâu và tôi phát hiện thế nào:
  - Lệnh kiểm quán trong skill vẫn dùng kho v1.0 sau khi đã lên v1.2. Chạy lại lệnh thì thấy mã 2.
  - AI ghi "một IdAllocator cho cả lượt", ngược với clarify #17. Đối chiếu `day.py` thì phát hiện ra.
  - AI đòi dòng `end` có `state: "paused"`. Đọc lại đề thì `paused` chỉ có ở snapshot.
- Điều tôi học được: `git fetch` trước khi nhận việc. Tôi làm trùng `day` với congvt vì không kéo code mới về.

# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 1 | 2026-11-21 P1 | Khách mới (chưa nấu) có `base_price`, `tip` bằng gì? PRD chỉ nói "chốt giá" khi bắt đầu nấu, "chốt boa" khi phục vụ. | Giả định: `null` tới khi chốt (`base_price` lúc `cook_started`, `tip` lúc `served`). Chưa hỏi Anh Năm. | Duc1306 + TADIZB |
| 2 | 2026-11-21 P1 | Id khách sinh mới theo họ nào? | Giả định: họ `C` (`C1`, `C2`…), nối sau hậu tố lớn nhất của khách fixture (IdAllocator). `order_id` = id khách. | Duc1306 + TADIZB |
| 3 | 2026-11-21 P1 | "Chọn đều theo seed" trong các món đủ nguyên liệu: cách bốc? | Món ứng viên sắp theo id (mã Unicode), bốc `randrange(n)` trên luồng RNG riêng `customer_dish`. | Duc1306 + TADIZB |
| 4 | 2026-11-21 P1 | Uy tín cộng/trừ số thực (0.2, −0.5) có thể sai số dấu phẩy động làm lệch `floor(reputation)` trong điểm. | Kẹp theo `reputation_min/max` rồi làm tròn 6 chữ số sau mỗi lần đổi. | Duc1306 + TADIZB |
| 5 | 2026-11-21 P1 | Khách rời sau khi trả tiền có phát `customer_left` không? | Không: `customer_left` chỉ có `reason` `patience`/`closing`; trả tiền xong rời bàn ngay chỉ phát `paid`. | Duc1306 + TADIZB |
| 6 | 2026-11-21 P1 | Khi hết ca, khách chờ có kiên nhẫn vừa về 0 rời với lý do gì? | `closing`, không trừ uy tín (PRD: "khi hết ca, khách còn chờ rời với closing"). | Duc1306 + TADIZB |
| 7 | 2026-11-21 P2 | Chế độ `day` (nối buổi sáng → buổi tối trong một tiến trình, `--mode day`, Test Contract v1.1) chạy thế nào: sự kiện chuyển buổi, bàn giao kho, điểm cả ngày? | Chưa có đề Phase 2 trong repo nên **chưa làm** `--mode day`. Tạm thời có `tools/choi_ngay_dem.py` nối hai tiến trình live qua file kho (đúng cơ chế Phase 1), chỉ để chơi thử; không đổi contract. Cần PO dán đề Phase 2. | congvt (chờ PO) |
| 8 | 2026-11-21 P1 | PRD mục 3 ghi "góc nhìn từ trên xuống cho nhà bè"; nhóm đang vẽ quán **góc chéo 3/4** theo ảnh mẫu. Có được không? | Giả định: được, vì PRD cho tự do đồ họa và luật vẫn là `[x,z]` nhìn từ trên (chỉ cách vẽ chéo). Cần PO/Anh Năm xác nhận; nếu không được thì phải vẽ lại quán nhìn thẳng từ trên (bản nháp nhìn từ trên chưa từng commit nên không lấy lại từ git được). | congvt (chờ PO) |

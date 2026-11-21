# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 1 | 2026-11-21 P1 | Khách mới (chưa nấu) có `base_price`, `tip` bằng gì? PRD chỉ nói "chốt giá" khi bắt đầu nấu, "chốt boa" khi phục vụ. | Giả định: `null` tới khi chốt (`base_price` lúc `cook_started`, `tip` lúc `served`). Chưa hỏi Anh Năm. | Duc1306 + TADIZB |
| 2 | 2026-11-21 P1 | Id khách sinh mới theo họ nào? | Giả định: họ `C` (`C1`, `C2`…), nối sau hậu tố lớn nhất của khách fixture (IdAllocator). `order_id` = id khách. | Duc1306 + TADIZB |
| 3 | 2026-11-21 P1 | "Chọn đều theo seed" trong các món đủ nguyên liệu: cách bốc? | Món ứng viên sắp theo id (mã Unicode), bốc `randrange(n)` trên luồng RNG riêng `customer_dish`. | Duc1306 + TADIZB |
| 4 | 2026-11-21 P1 | Uy tín cộng/trừ số thực (0.2, −0.5) có thể sai số dấu phẩy động làm lệch `floor(reputation)` trong điểm. | Kẹp theo `reputation_min/max` rồi làm tròn 6 chữ số sau mỗi lần đổi. | Duc1306 + TADIZB |
| 5 | 2026-11-21 P1 | Khách rời sau khi trả tiền có phát `customer_left` không? | Không: `customer_left` chỉ có `reason` `patience`/`closing`; trả tiền xong rời bàn ngay chỉ phát `paid`. | Duc1306 + TADIZB |
| 6 | 2026-11-21 P1 | Khi hết ca, khách chờ có kiên nhẫn vừa về 0 rời với lý do gì? | `closing`, không trừ uy tín (PRD: "khi hết ca, khách còn chờ rời với closing"). | Duc1306 + TADIZB |

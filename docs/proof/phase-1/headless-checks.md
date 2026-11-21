# Kiểm chứng headless Phase 1 (chạy thật)

Tạo bởi script kiểm chứng; đầu vào/đầu ra nằm cạnh file này (`smoke/`, `g/`).

## 1. Smoke hộp đen gather → quán (Test Contract, cuối mục G)
- gather_end: {"reason": "docked", "inventory": {"items": {"bong_sung": 2, "ca_loc": 1}}}
- catch.json: {"items": {"bong_sung": 2, "ca_loc": 1}}  · quan tick 0 stock: {"bong_sung": 2, "ca_loc": 1}
- ĐẠT: True

## 2. Ngất: kho rỗng, bỏ giỏ LIFO
- exit=0 · faint={"cause": "choke", "lost": ["bong_sung", "ca_loc"], "hp": 0} · end.reason=fainted · kho={"items": {}}
- ĐẠT: True

## 3. Chạm --ticks trước khi kết thúc buổi sáng: không tạo file kho
- exit=0 · end.reason=tick_limit · file kho tồn tại: False
- ĐẠT: True

## 4. Hết giờ buổi sáng: kết thúc `time`, giữ giỏ vào kho
- exit=0 · end.reason=time · ticks=3 · kho={"items": {"bong_sung": 1}}
- ĐẠT: True

## 5. Một ngày, 2 tiến trình dùng chung file kho
- gather exit=0 · event: gather, dive, fish_caught, surface, gather_end
- end.reason=docked · kho={"items": {"bong_dien_dien": 1, "ca_linh": 3}}
- quán exit=0 · tick 0 stock={"bong_dien_dien": 1, "ca_linh": 3} · event: [(120, 'customer_arrived')]
- ĐẠT (quán nhận đúng kho): True

## 6. Tất định: chạy lại cùng seed/đầu vào
- sha256 gather 0f4e3110fbf73fc7 = 0f4e3110fbf73fc7 · kho 453e124126abf4a6 = 453e124126abf4a6 · quán 9ac2d7fea38d3f9d = 9ac2d7fea38d3f9d
- ĐẠT: True

## 7. Đầu vào sai → mã 2, chẩn đoán qua stderr
- tick lặp: exit=2 (đầu vào sai: frame 1: tick trùng hoặc giảm)
- kind lạ trong kho: exit=2 (đầu vào sai: nguyên liệu lạ: ca_map)
- --inventory-out với quan: exit=2 (đầu vào sai: --inventory-out chỉ dùng với gather)
- ĐẠT: True

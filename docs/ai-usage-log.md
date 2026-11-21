# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| P1 | congvt | Claude Code (Claude Opus 5.5) | Skill `thiet-ke-do-hoa`; đồ họa/HUD/thoại trong `chonoi/web/index.html`; `tools/choi_ngay_dem.py`; kiểm chứng Phase 1 (`docs/proof/phase-1/`, `docs/verification/phase-1.md`) | Không đo được | AI đọc `stove.dish` là chuỗi trong khi contract là object (`[object Object]`); bản đầu HUD hiện tồn vật lý thay vì kho khả dụng; ghi nhầm trong clarify #8 rằng bản quán nhìn từ trên còn trong git. Đều đã sửa sau khi chạy thử. |
| P2 | Duc1306 + TADIZB | Claude Code (Claude Opus 5.5) | Phần A (gather v1.1: cá bơi/sinh, Cá Sấu, Máu/ngất do quái) và B (quán: 2 bếp/4 bàn, 6 món, kế hoạch D1–D5, lọc món theo kế hoạch); contract v1.1 + kiểm tuning/scenario; 42 test mới | Không đo được | Bản đầu so điểm đến waypoint bằng `<=` thuần nên M1 tới [64,24] trễ 1 tick do sai số cộng dồn; test đầu so vị trí 6 chữ số trong khi JSONL làm tròn 3 chữ số. Đã sửa sau khi chạy test. |

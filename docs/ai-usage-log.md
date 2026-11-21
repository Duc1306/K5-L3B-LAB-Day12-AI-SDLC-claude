# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| P1 | congvt | Claude Code (Claude Opus 5.5) | Skill `thiet-ke-do-hoa`; đồ họa/HUD/thoại trong `chonoi/web/index.html`; `tools/choi_ngay_dem.py`; kiểm chứng Phase 1 (`docs/proof/phase-1/`, `docs/verification/phase-1.md`) | Không đo được | AI đọc `stove.dish` là chuỗi trong khi contract là object (`[object Object]`); bản đầu HUD hiện tồn vật lý thay vì kho khả dụng; ghi nhầm trong clarify #8 rằng bản quán nhìn từ trên còn trong git. Đều đã sửa sau khi chạy thử. |

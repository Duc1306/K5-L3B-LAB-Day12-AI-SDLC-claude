"""Lối tắt giữ cho lệnh cũ: chơi liền mạch sáng → tối → sáng… Xem `chonoi/ngay_dem.py`.

    python tools/choi_ngay_dem.py [--port 8000] [--seed 1] [--so-ngay N] [--nghi 4]

Tương đương: python -m chonoi.ngay_dem ...
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chonoi.ngay_dem import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())

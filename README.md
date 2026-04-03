# EnviSoft Alert Demo Docker

Demo cảnh báo ô nhiễm đa trạm bằng Docker + Streamlit.

## Ý tưởng
- Có 8 file dữ liệu: 4 file bình thường và 4 file ô nhiễm.
- Mỗi file là 1 trạm khác nhau.
- Hệ thống đọc chỉ số, so với ngưỡng demo, và phát cảnh báo nếu vượt ngưỡng.
- Khi có cảnh báo, giao diện hiển thị:
  - trạm cảnh báo
  - chỉ số vượt ngưỡng
  - camera của trạm
  - AI dự đoán từ ảnh
  - âm thanh cảnh báo

## Chạy lần đầu
```bash
docker compose up --build
```

Mở trình duyệt tại:

```text
http://localhost:8501
```

## Chạy các lần sau
```bash
docker compose up
```

## Nếu chỉ muốn chạy lại bước khởi tạo dữ liệu
```bash
docker compose run --rm init_data
```

## Cấu trúc chính
- `data/scenarios/normal`: 4 file bình thường
- `data/scenarios/polluted`: 4 file ô nhiễm
- `data/camera`: ảnh camera normal/polluted
- `data/processed`: dữ liệu sau parse + chuẩn hóa
- `db/demo.db`: SQLite demo
- `app/main.py`: dashboard Streamlit

## Lưu ý
Dự án mount toàn bộ thư mục vào `/app`, nên khi sửa code Python thông thường bạn không cần build lại image.

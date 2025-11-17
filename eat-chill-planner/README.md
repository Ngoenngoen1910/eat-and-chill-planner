# Eat & Chill Planner 🗺️

Đây là dự án ứng dụng lập lịch trình ăn uống và giải trí, sử dụng OpenStreetMap, OSRM, Streamlit, FastAPI và Ollama.

---

## ⚙️ Yêu cầu cài đặt (Bắt buộc)

Trước khi chạy, bạn cần cài đặt 2 phần mềm sau:

1.  **Python 3.10+**
2.  **Ollama:** Tải và cài đặt Ollama (phiên bản Desktop) từ [ollama.com](https://ollama.com/).

---

## 🚀 Hướng dẫn cài đặt & Chạy (3 bước)

### Bước 1: Tải Model AI (Làm 1 lần duy nhất)

Sau khi cài đặt Ollama, bạn cần tải model AI mà chatbot sử dụng. Mở **PowerShell** hoặc **CMD** và chạy:

```bash
# Tải model 1 tỷ tham số (nhẹ, ~1.7GB) mà code đang dùng
ollama pull llama3.2:1b
```

### Bước 2: Cài đặt thư viện Python

1.  Mở Terminal, di chuyển đến thư mục gốc của dự án (`eat-chill-planner`).
2.  (Khuyến khích) Tạo môi trường ảo:
    ```bash
    python -m venv venv
    ```
3.  Kích hoạt môi trường ảo:
    ```bash
    # Trên Windows
    .\venv\Scripts\activate
    ```
4.  Cài đặt tất cả các gói thư viện cần thiết:
    ```bash
    pip install -r requirements.txt
    ```

### Bước 3: Chạy ứng dụng (Cần 3 Terminal)

Bạn cần mở 3 Terminal (hoặc 3 tab Terminal) riêng biệt tại thư mục gốc của dự án.

#### 🖥️ Terminal 1: Bật Server AI
Bạn chỉ cần **mở ứng dụng Ollama (Desktop App)**. Ứng dụng sẽ tự động chạy ngầm một server tại `http://127.0.0.1:11434`.

#### ⚙️ Terminal 2: Chạy Backend (FastAPI)
Ở Terminal này, chạy lệnh:

```bash
# Đảm bảo bạn đang ở thư mục gốc
uvicorn backend.main:app --reload
```
Bạn sẽ thấy thông báo: `Uvicorn running on http://127.0.0.1:8000`

#### 🌐 Terminal 3: Chạy Frontend (Streamlit)
Ở Terminal cuối cùng, chạy lệnh:

```bash
# Đảm bảo bạn đang ở thư mục gốc
streamlit run frontend/app.py
```
Trình duyệt sẽ tự động mở trang `http://localhost:8501`. Đây là giao diện chính của ứng dụng.
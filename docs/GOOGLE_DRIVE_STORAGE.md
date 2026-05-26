# Google Drive Storage Setup

Backend đã đổi từ MinIO sang Google Drive. Với chạy local hoặc Google Drive cá nhân, dùng **OAuth Desktop Client**. Không dùng Service Account với My Drive cá nhân vì Service Account không có storage quota riêng.

## 1. Tạo OAuth Desktop Client

1. Vào Google Cloud Console.
2. Bật `Google Drive API`.
3. Vào `APIs & Services` → `OAuth consent screen`.
4. Chọn `External`, điền app name và email.
5. Vào `APIs & Services` → `Credentials`.
6. Chọn `Create Credentials` → `OAuth client ID`.
7. Application type: `Desktop app`.
8. Tải file JSON xuống.
9. Đổi tên thành:

```text
google-drive-oauth-client.json
```

10. Đặt vào:

```text
credentials/google-drive-oauth-client.json
```

## 2. Cấu hình .env

```env
STORAGE_PROVIDER=google_drive
STORAGE_ROOT_PREFIX=STEM

GOOGLE_DRIVE_AUTH_MODE=oauth
GOOGLE_DRIVE_OAUTH_CLIENT_FILE=./credentials/google-drive-oauth-client.json
GOOGLE_DRIVE_OAUTH_TOKEN_FILE=./credentials/google-drive-token.json
GOOGLE_DRIVE_ROOT_FOLDER_ID=ID_FOLDER_GOOGLE_DRIVE_CUA_BAN
GOOGLE_DRIVE_MAKE_PUBLIC=false
```

`GOOGLE_DRIVE_ROOT_FOLDER_ID` là phần ID trong link folder Drive.

Ví dụ:

```text
https://drive.google.com/drive/folders/1QkAe0G_20lIwZAHi-oZ_OGoVlP0SDeP9
```

thì:

```env
GOOGLE_DRIVE_ROOT_FOLDER_ID=1QkAe0G_20lIwZAHi-oZ_OGoVlP0SDeP9
```

## 3. Chạy lần đầu

```powershell
cd "D:\AG Project\STEM"
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
$env:PYTHONPATH="backend"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Khi upload file lần đầu, trình duyệt sẽ mở để bạn đăng nhập Google. Hãy chọn tài khoản Google đang sở hữu folder Drive gốc.

Sau khi đăng nhập thành công, backend tự tạo:

```text
credentials/google-drive-token.json
```

Từ lần sau không cần đăng nhập lại nếu token còn hợp lệ.

## 4. Service Account chỉ dùng với Shared Drive

Nếu đặt:

```env
GOOGLE_DRIVE_AUTH_MODE=service_account
```

thì `GOOGLE_DRIVE_ROOT_FOLDER_ID` phải là folder nằm trong Shared Drive, không phải My Drive cá nhân. Nếu dùng My Drive cá nhân, Google sẽ báo:

```text
Service Accounts do not have storage quota
```

Với project chạy local, cứ dùng `GOOGLE_DRIVE_AUTH_MODE=oauth`.

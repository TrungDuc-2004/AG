# STEM FastAPI Google Drive MongoDB PostgreSQL Neo4j

Project dùng FastAPI + MongoDB để quản lý học liệu STEM, lưu file gốc trên Google Drive, sau đó tự sync metadata sang PostgreSQL và Neo4j.

## Thiết kế storage hiện tại

File gốc được lưu trên Google Drive bằng Service Account. MongoDB vẫn là source of truth cho metadata.

Biến môi trường chính:

```env
STORAGE_PROVIDER=google_drive
STORAGE_ROOT_PREFIX=STEM
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-drive-service-account.json
GOOGLE_DRIVE_ROOT_FOLDER_ID=your_drive_folder_id
GOOGLE_DRIVE_MAKE_PUBLIC=false
```

Logical path/objectKey:

```txt
STEM/{classSlug}/{entityType}/{entitySlug}/{fileName}
```

Ví dụ:

```txt
STEM/lop-11/documents/binh-loc-nuoc/hoa-11-binh-loc-nuoc.docx
STEM/lop-11/concepts/loc-nuoc-hap-phu/ly-thuyet-loc-nuoc.pdf
STEM/lop-11/topics/nuoc-dung-dich/tong-quan-chu-de.docx
STEM/lop-11/subjects/hoa-hoc/chuong-trinh-hoa-hoc.docx
```

Trên MongoDB, document sẽ lưu dạng:

```json
{
  "storage": {
    "provider": "google_drive",
    "objectKey": "STEM/lop-11/documents/binh-loc-nuoc/file.pdf",
    "rootFolderId": "...",
    "folderId": "...",
    "fileId": "...",
    "webViewLink": "...",
    "webContentLink": "...",
    "mimeType": "application/pdf",
    "sizeBytes": 123456
  }
}
```

## Setup Google Drive

1. Enable Google Drive API trong Google Cloud Console.
2. Tạo Service Account.
3. Download key JSON.
4. Đặt key tại:

```txt
credentials/google-drive-service-account.json
```

5. Tạo folder gốc trên Google Drive, ví dụ `STEM_STORAGE`.
6. Share folder đó cho email Service Account với quyền `Editor`.
7. Copy folder ID vào `.env`:

```env
GOOGLE_DRIVE_ROOT_FOLDER_ID=your_drive_folder_id
```

Xem hướng dẫn chi tiết trong `docs/GOOGLE_DRIVE_STORAGE.md`.

## MongoDB collections

Backend chỉ tự tạo các collection chính:

```txt
classes
subjects
topics
concepts
documents
users
```

Không tạo collection `roles` và `typedocs`. `role` trong `users` và `typedocs` trong `documents` chỉ là field.

## PostgreSQL và Neo4j sync

Backend có thể tự tạo:

```txt
PostgreSQL database: stem_learning_pg
PostgreSQL tables: class, subject, topic, concept, document, app_user, class_subject, doc_concept, doc_type, typedoc, roles, log
Neo4j constraints + root node: (:Thing {thing_name: "STEM"})
```

Lưu ý: `roles` và `typedoc` trong PostgreSQL là bảng quan hệ để phục vụ schema SQL, không phải MongoDB collection. Dữ liệu trong đó được tự suy ra từ field `users.role` và `documents.typedocs`.

Neo4j dùng light-node theo file `Neo4j.cypher`:

```txt
(:Thing)-[:HAS_CLASS]->(:Class)
(:Class)-[:HAS_SUBJECT]->(:Subject)
(:Subject)-[:HAS_TOPIC]->(:Topic)
(:Topic)-[:HAS_CONCEPT]->(:Concept)
(:Document)-[:BELONGS_TO_TOPIC]->(:Topic)
(:Document)-[:COVERS_CONCEPT]->(:Concept)
(:Concept)-[:HAS_DOCUMENT]->(:Document)
```

## API không dùng /v1

```txt
GET  /api/health
POST /api/classes
POST /api/users
POST /api/subjects
POST /api/topics
POST /api/concepts
POST /api/documents
```

Các endpoint tạo dữ liệu đã đổi sang Form input, không bắt nhập JSON. Subject/Topic/Concept có thể upload file ngay trong form. Document cũng dùng Form input ngay tại `POST /api/documents`, có ô chọn file trong Swagger; không cần nhập JSON và không cần tự nhập objectKey.

Endpoint cũ vẫn giữ để không vỡ frontend:

```txt
GET /api/files/documents/{map_id}/presigned-url
GET /api/files/documents/{map_id}/download
```

Với Google Drive, endpoint này trả Drive view URL, không phải MinIO presigned URL.

## API sync

```txt
GET  /api/sync/health
GET  /api/sync/check-mongo
POST /api/sync/init-targets
POST /api/sync/all
POST /api/sync/{entity}/{map_id}
```

Ví dụ:

```txt
POST /api/sync/init-targets
POST /api/sync/all
POST /api/sync/documents/HH11_T1_C1_D1
```

Nếu `AUTO_SYNC_ENABLED=true`, sau khi tạo/upload entity ở MongoDB, backend sẽ tự sync entity đó sang PostgreSQL + Neo4j. Nếu PostgreSQL/Neo4j đang tắt, việc upload MongoDB/Google Drive vẫn không bị hỏng; bạn có thể bật service rồi gọi `POST /api/sync/all` để backfill.

## Chạy bằng Docker Compose

Đặt file credential vào `credentials/google-drive-service-account.json`, sửa `.env`, rồi chạy:

```bash
docker compose up --build
```

Mở:

```txt
Frontend:       http://localhost:5173
Backend docs:   http://localhost:8000/docs
Neo4j Browser:  http://localhost:7474
PostgreSQL:     localhost:5432
MongoDB:        localhost:27017
```

Tài khoản mặc định:

```txt
Neo4j: neo4j / password123
Postgres: postgres / postgres
```

## Chạy local bằng venv

Bạn cần chạy local các service sau: MongoDB, PostgreSQL, Neo4j. Google Drive không cần service local, chỉ cần credential JSON và folder ID.

Chạy backend:

```bash
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
$env:PYTHONPATH="backend"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Cách trên giúp backend đọc `.env` ở thư mục root và vẫn import được package `app`.

Chạy frontend:

```bash
cd frontend
npm install
npm run dev
```

## Quy trình test nhanh

1. Mở frontend hoặc Swagger.
2. Tạo Class.
3. Tạo User.
4. Tạo Subject, có thể kèm file.
5. Tạo Topic, có thể kèm file.
6. Tạo Concept, có thể kèm file.
7. Tạo Document bằng form, chọn file gốc rồi submit.
8. Gọi `GET /api/sync/check-mongo` để kiểm tra Mongo đủ quan hệ chưa.
9. Gọi `POST /api/sync/all` nếu muốn backfill toàn bộ dữ liệu sang PostgreSQL + Neo4j.

Khi tạo Document, backend tự upload file lên Google Drive, tự sinh `storage.objectKey`, lưu metadata vào MongoDB `documents`, rồi tự sync sang PostgreSQL + Neo4j nếu `AUTO_SYNC_ENABLED=true`.

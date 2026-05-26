# STEM + AI-Extract + Search Integration

Bản này hợp nhất 3 phần:

1. STEM data warehouse: MongoDB + Google Drive metadata + PostgreSQL + Neo4j sync.
2. AI-Extract: upload PDF, extract topic/lesson/chunk/keyword, finalize chunk bằng Kaggle cutline.
3. Keyword Search: search keyword qua Neo4j TopicBag + Keyword + Document.

## Nguyên tắc tích hợp

Logic cắt chunk của AI-Extract được giữ nguyên. Phần lưu Drive/metadata/sync chỉ được gọi thêm sau các API approve/finalize.

- Approve topics: lưu `topics_approved.json`, upload topic PDF nếu có, tạo/sync Topic.
- Approve lessons: lưu `lessons_approved.json`, upload lesson PDF nếu có, tạo/sync Concept.
- Approve chunks: chỉ approve chunk JSON, chưa lưu Document vì PDF chunk cuối cần qua finalize.
- Finalize lesson chunks: chạy Kaggle cutline + keyword extraction như cũ, sau đó upload chunk PDF, tạo Document, keysearch, Keyword, DocumentKeyword, TopicBag, sync PostgreSQL/Neo4j.
- Approve keywords: ghi `keywords_approved.json`, cập nhật lại keysearch/Keyword/DocumentKeyword/TopicBag/sync cho các Document đã finalize.

## Mapping chính

- `topic_id = topic.name`, `TOPIC.name = topic.title`
- `concept_id = lesson.name`, `CONCEPT.name = lesson.heading + " - " + lesson.title`
- `document_id = lesson.name + "_" + chunk.name`
- `DOCUMENT.title = chunk.heading + " " + chunk.title`
- `DOCUMENT.topic_id = lesson.topic_name`
- `DOCUMENT.keysearch = keyword_name` của chunk, ghép bằng dấu phẩy
- `DOC_CONCEPT = lesson/concept -> chunk/document`
- `DOCUMENT_KEYWORD` sinh từ keysearch
- `TOPIC_BAG` được rebuild sau mỗi document sync

## API flow test

1. `POST /api/extract/jobs` upload PDF.
2. `POST /api/extract/jobs/{job_id}/topics/extract?offset=auto&split_pdf=true`.
3. `POST /api/extract/jobs/{job_id}/topics/approve?subjectMapId=subject_vl10&classMapId=class_10`.
4. `POST /api/extract/jobs/{job_id}/lessons/build`.
5. `POST /api/extract/jobs/{job_id}/lessons/approve`.
6. `POST /api/extract/jobs/{job_id}/chunks/lesson/{lesson_name}/extract`.
7. `POST /api/extract/jobs/{job_id}/chunks/lesson/{lesson_name}/approve`.
8. `POST /api/extract/jobs/{job_id}/chunks/lesson/{lesson_name}/finalize`.
9. Optionally review/update keywords, then `POST /api/extract/jobs/{job_id}/keywords/lesson/{lesson_name}/approve`.
10. Search: `POST /api/search/keyword` with body `{"query":"...","limit":5}`.

## Config

- Backend `.env`: DB, Google Drive, storage, Neo4j, embedding config.
- `backend/app/core/config.env`: Gemini + Kaggle keys. See `backend/app/core/config.env.example`.

## Notes

- Topic approval needs `subjectMapId`. If that subject does not exist yet, pass `classMapId` too, or set `AI_EXTRACT_DEFAULT_SUBJECT_MAP_ID` and `AI_EXTRACT_DEFAULT_CLASS_MAP_ID`.
- Chunk documents are persisted only after `finalize`, because before finalize the PDF boundaries may still be provisional.
- `GOOGLE_DRIVE_ROOT_FOLDER_ID` must be configured before approve/finalize persistence can upload files.

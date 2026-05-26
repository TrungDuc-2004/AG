# Kiểm tra MongoDB có đủ để sync PostgreSQL và Neo4j không

## Kết luận
MongoDB hiện tại **đủ để sync sang PostgreSQL và Neo4j**, với điều kiện các quan hệ sau tồn tại đầy đủ:

```txt
Subject.classMapId  -> Class.map_id
Topic.subjectMapId  -> Subject.map_id
Concept.topicMapId  -> Topic.map_id
Document.conceptMapId -> Concept.map_id
```

## Điểm khớp

| MongoDB | PostgreSQL | Neo4j |
|---|---|---|
| classes.map_id/name | class.mongo_map_id/name/grade | (:Class {pg_id, mongo_map_id, class_name}) |
| subjects.classMapId/name | subject + class_subject | (:Class)-[:HAS_SUBJECT]->(:Subject) |
| topics.subjectMapId/name | topic.subject_id | (:Subject)-[:HAS_TOPIC]->(:Topic) |
| concepts.topicMapId/name | concept.topic_id | (:Topic)-[:HAS_CONCEPT]->(:Concept) |
| documents.conceptMapId/storage.objectKey | document + doc_concept + doc_type | (:Document)-[:COVERS_CONCEPT]->(:Concept), (:Concept)-[:HAS_DOCUMENT]->(:Document) |

## Điểm cần suy luận khi sync

1. PostgreSQL bảng `class` cần `grade INTEGER`, còn MongoDB có `map_id/name`. Code sẽ tự parse số lớp từ `map_id` hoặc `name`.
2. PostgreSQL có bảng `roles` và `typedoc`, nhưng MongoDB không cần collection riêng. Code sẽ tự tạo dòng tương ứng từ field `users.role` và `documents.typedocs`.
3. PostgreSQL document có `topic_id`, còn MongoDB document chỉ có `conceptMapId`. Code sẽ đi ngược:

```txt
Document.conceptMapId -> Concept.topicMapId -> Topic
```

4. Neo4j dùng `pg_id` để liên kết về PostgreSQL, đồng thời lưu thêm `mongo_map_id` để debug.

## API kiểm tra

```txt
GET /api/sync/check-mongo
```

API này kiểm tra thiếu collection, thiếu field quan hệ, hoặc reference sai.

from app.models.base import mongo_dump
from app.models.class_model import ClassModel
from app.models.concept_model import ConceptModel
from app.models.subject_model import SubjectModel
from app.models.topic_model import TopicModel
from app.models.user_model import UserModel
from app.repositories.learning_repository import (
    ClassRepository,
    ConceptRepository,
    SubjectRepository,
    TopicRepository,
    UserRepository,
)


class SeedService:
    def __init__(self) -> None:
        self.classes = ClassRepository()
        self.subjects = SubjectRepository()
        self.topics = TopicRepository()
        self.concepts = ConceptRepository()
        self.users = UserRepository()

    async def seed_mongo_sample(self) -> dict:
        class_doc = await self.classes.upsert_by_map_id(
            "10", mongo_dump(ClassModel(map_id="10", name="Lớp 10"))
        )
        subject_doc = await self.subjects.upsert_by_map_id(
            "TH10",
            mongo_dump(
                SubjectModel(
                    map_id="TH10",
                    name="Tin học",
                    filePath="",
                    classMapId="10",
                    description="Học liệu STEM môn Tin học lớp 10",
                )
            ),
        )
        topic_doc = await self.topics.upsert_by_map_id(
            "TH10_T1",
            mongo_dump(
                TopicModel(
                    map_id="TH10_T1",
                    subjectMapId="TH10",
                    name="Máy tính và cộng đồng",
                    description="Chủ đề STEM thuộc môn Tin học lớp 10",
                    topicNumber=1,
                    periodCount=3,
                    filePath="",
                )
            ),
        )
        concept_doc = await self.concepts.upsert_by_map_id(
            "TH10_T1_C1",
            mongo_dump(
                ConceptModel(
                    map_id="TH10_T1_C1",
                    topicMapId="TH10_T1",
                    name="Thông tin và dữ liệu",
                    filePath="",
                    definition="Thông tin là những gì đem lại hiểu biết cho con người; dữ liệu là thông tin được biểu diễn dưới dạng có thể lưu trữ và xử lý.",
                    conceptNumber=1,
                )
            ),
        )
        user_doc = await self.users.upsert_by_map_id(
            "USER_001",
            mongo_dump(
                UserModel(
                    map_id="USER_001",
                    name="Nguyễn Văn A",
                    email="nguyenvana@example.com",
                    gender="male",
                    address="123 Đường ABC, Phường XYZ, Quận 1, TP.HCM",
                    role="1",
                    avatarImage="https://example.com/avatars/user001.jpg",
                )
            ),
        )
        return {
            "message": "Seeded sample data from mongo.json",
            "classes": class_doc,
            "subjects": subject_doc,
            "topics": topic_doc,
            "concepts": concept_doc,
            "users": user_doc,
        }

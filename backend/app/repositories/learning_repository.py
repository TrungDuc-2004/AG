from app.repositories.base_repository import MongoRepository


class ClassRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("classes")


class SubjectRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("subjects")


class TopicRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("topics")


class ConceptRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("concepts")


class DocumentRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("documents")


class UserRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("users")


class RoleRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("roles")


class TypeDocRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("typedocs")


class KeywordRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("keywords")


class DocumentKeywordRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("document_keywords")


class TopicBagRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("topic_bags")


class DocumentMetadataRepository(MongoRepository):
    def __init__(self) -> None:
        super().__init__("document_metadata")

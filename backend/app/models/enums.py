from enum import Enum


class EntityType(str, Enum):
    subjects = "subjects"
    topics = "topics"
    concepts = "concepts"
    documents = "documents"

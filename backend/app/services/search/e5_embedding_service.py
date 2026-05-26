from embedding_utils import e5_embed_passage, e5_embed_query


class E5EmbeddingService:
    def embed_query(self, text: str) -> list[float]:
        return e5_embed_query(text)

    def embed_passage(self, text: str) -> list[float]:
        return e5_embed_passage(text)

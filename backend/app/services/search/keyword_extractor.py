import re

from app.services.search.text_normalizer import TextNormalizer


class KeywordExtractor:
    STOPWORDS = {
        "là", "của", "và", "hoặc", "trong", "ngoài", "với", "cho",
        "tôi", "em", "anh", "chị", "hãy", "tìm", "kiếm", "về", "theo",
        "các", "những", "một", "này", "đó", "gì", "như", "thế", "nào",
        "được", "không", "bài", "mục", "phần", "nêu", "cho", "biết",
    }

    def extract(self, query: str, max_keywords: int = 8) -> list[str]:
        normalized = TextNormalizer.normalize(query)
        if not normalized:
            return []

        # Luôn giữ nguyên query làm candidate đầu tiên để bắt các cụm dài
        # như "đơn vị lưu trữ dữ liệu" nếu keyword đó có trong topic_bag.
        merged: list[str] = [normalized]

        tokens = re.findall(r"[\wÀ-ỹ]+", normalized, flags=re.UNICODE)
        tokens = [t.strip() for t in tokens if t.strip()]

        # Query ngắn thường chính là keyword chính.
        if len(tokens) <= 4:
            return merged[:max_keywords]

        # Tạo cụm 2-3 từ để bắt keyword/alias trong topic_bag.
        phrases: list[str] = []
        for n in (3, 2):
            for i in range(len(tokens) - n + 1):
                window = tokens[i : i + n]
                if any(w in self.STOPWORDS for w in window):
                    continue
                phrases.append(" ".join(window))

        candidates = []
        for t in tokens:
            if t not in self.STOPWORDS and len(t) > 1:
                candidates.append(t)

        for item in phrases + candidates:
            if item not in merged:
                merged.append(item)

        return merged[:max_keywords]

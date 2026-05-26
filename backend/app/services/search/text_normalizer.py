import re
import unicodedata


class TextNormalizer:
    @staticmethod
    def normalize(text: str) -> str:
        if not text:
            return ""
        text = unicodedata.normalize("NFC", text)
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def remove_vietnamese_accents(text: str) -> str:
        text = unicodedata.normalize("NFD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        text = text.replace("đ", "d").replace("Đ", "D")
        return text

    @staticmethod
    def normalize_for_compare(text: str) -> str:
        text = TextNormalizer.normalize(text)
        text = TextNormalizer.remove_vietnamese_accents(text)
        text = re.sub(r"[^a-z0-9\s]+", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

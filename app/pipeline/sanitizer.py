import re
import hashlib
from typing import Dict

from app.pipeline.logger import get_pipeline_logger

log = get_pipeline_logger("sanitizer")


class PIISanitizer:
    def __init__(self, policy: str = "mask") -> None:
        self.policy = policy.lower()  # "mask", "remove", "tokenize"
        log.info(f"PIISanitizer initialized with policy: {self.policy}")

        # Compile PII detection regex patterns
        self.patterns = {
            "EMAIL": re.compile(
                r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b"
            ),
            "PHONE": re.compile(
                r"(?:\+?\d{1,3}[-.\s]?)?\b(?:\d{3}[-.\s]?\d{3}[-.\s]?\d{4}|\d{5}[-.\s]?\d{5}|\d{10})\b"
            ),
            "PAN": re.compile(
                r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"
            ),
            "CREDIT_CARD": re.compile(
                r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
            ),
            "AADHAAR": re.compile(
                r"\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b"
            ),
            "PASSPORT": re.compile(
                r"\b(?:[A-Z][0-9]{7,8}|[0-9]{9})\b"
            ),
            "IP_ADDRESS": re.compile(
                r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
            ),
        }

    def sanitize(self, text: str) -> str:
        if not text:
            return text

        sanitized = text
        for pii_type, pattern in self.patterns.items():
            def replacer(match: re.Match) -> str:
                original_value = match.group(0)
                if self.policy == "remove":
                    return ""
                elif self.policy == "tokenize":
                    h = hashlib.sha256(original_value.encode()).hexdigest()[:8]
                    return f"[TOKEN:{pii_type}:{h}]"
                else:  # default "mask"
                    return f"[{pii_type}]"

            sanitized = pattern.sub(replacer, sanitized)

        return sanitized

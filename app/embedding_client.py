from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
from urllib import error, request


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9À-ÿ]+")


def normalize_text(text: str) -> str:
    return " ".join(TOKEN_PATTERN.findall((text or "").lower()))


def tokenize(text: str) -> set[str]:
    return set(normalize_text(text).split())


def fuzzy_token_overlap(left: str, right: str) -> float:
    left_tokens = [token for token in normalize_text(left).split() if token]
    right_tokens = [token for token in normalize_text(right).split() if token]
    if not left_tokens or not right_tokens:
        return 0.0

    matches = 0
    used_right_indexes: set[int] = set()
    for left_token in left_tokens:
        for index, right_token in enumerate(right_tokens):
            if index in used_right_indexes:
                continue
            if _tokens_match(left_token, right_token):
                matches += 1
                used_right_indexes.add(index)
                break

    denominator = max(len(left_tokens), len(right_tokens))
    if denominator == 0:
        return 0.0
    return matches / denominator


def _tokens_match(left: str, right: str) -> bool:
    if left == right:
        return True
    common_prefix_length = 0
    for left_char, right_char in zip(left, right):
        if left_char != right_char:
            break
        common_prefix_length += 1
    return common_prefix_length >= 5


def cosine_similarity(left: List[float], right: List[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def lexical_similarity(left: str, right: str) -> float:
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    strict_score = 0.0
    if left_tokens and right_tokens:
        intersection = len(left_tokens & right_tokens)
        union = len(left_tokens | right_tokens)
        if union > 0:
            strict_score = intersection / union

    fuzzy_score = fuzzy_token_overlap(left, right)
    return max(strict_score, fuzzy_score)


def load_local_env() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    for env_name in (".env", ".env.example"):
        env_path = repo_root / env_name
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


class EmbeddingClient:
    def __init__(self) -> None:
        load_local_env()
        self.api_url = self._normalize_api_url(os.getenv("EMBEDDINGS_API_URL", "https://embeddings.myia.io/v1/embeddings"))
        self.api_key = os.getenv("EMBEDDINGS_API_KEY", "")
        self.model = os.getenv("EMBEDDINGS_MODEL", "qwen3-4b-awq-embedding")
        self.timeout_seconds = float(os.getenv("EMBEDDINGS_TIMEOUT_SECONDS", "20"))
        self._similarity_cache: Dict[Tuple[str, str], Tuple[float, str]] = {}

    def mode(self) -> str:
        return "remote" if self.api_key else "fallback"

    def similarity(self, left: str, right: str) -> Tuple[float, str]:
        normalized_left = normalize_text(left)
        normalized_right = normalize_text(right)
        if not normalized_left or not normalized_right:
            return 0.0, "lexical_fallback"

        cache_key = tuple(sorted((normalized_left, normalized_right)))
        if cache_key in self._similarity_cache:
            return self._similarity_cache[cache_key]

        if self.api_key:
            try:
                similarity = self._remote_similarity(normalized_left, normalized_right)
                result = similarity, "embedding"
                self._similarity_cache[cache_key] = result
                return result
            except (error.URLError, error.HTTPError, TimeoutError, ValueError, KeyError, json.JSONDecodeError):
                pass

        similarity = lexical_similarity(normalized_left, normalized_right)
        result = similarity, "lexical_fallback"
        self._similarity_cache[cache_key] = result
        return result

    def _remote_similarity(self, left: str, right: str) -> float:
        payload = json.dumps(
            {
                "model": self.model,
                "input": [left, right],
            }
        ).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Key": self.api_key,
        }
        http_request = request.Request(self.api_url, data=payload, headers=headers, method="POST")
        with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))

        data = body["data"]
        left_vector = data[0]["embedding"]
        right_vector = data[1]["embedding"]
        return max(0.0, min(1.0, cosine_similarity(left_vector, right_vector)))

    def _normalize_api_url(self, api_url: str) -> str:
        normalized = api_url.rstrip("/")
        if normalized.endswith("/embeddings"):
            return normalized
        if normalized.endswith("/v1"):
            return normalized + "/embeddings"
        return normalized

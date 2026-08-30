from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .storage import GenesisStore
from .util import new_id, utc_now

CODE_ARTIFACT_SCHEMA = "migi-code-artifact.v0"
VALID_SOURCE_KINDS = {"chat", "log", "repository", "file", "generated", "external"}
VALID_STATUSES = {"concept", "specification", "prototype", "executable", "tested", "deprecated"}


@dataclass(frozen=True)
class CodeSource:
    kind: str
    uri: str
    path: str | None = None
    revision: str | None = None
    conversation_id: str | None = None
    message_id: str | None = None

    def validate(self) -> None:
        if self.kind not in VALID_SOURCE_KINDS:
            raise ValueError(f"Unsupported code source kind: {self.kind}")
        if not self.uri:
            raise ValueError("Code source URI is required")

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True)
class CodeArtifact:
    schema_version: str
    artifact_id: str
    title: str
    language: str
    format: str
    content: str
    source: CodeSource
    status: str
    created_at: str
    content_hash: str
    named_systems: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    runtime_adapter: str | None = None
    parent_artifact_id: str | None = None
    receipt_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        title: str,
        language: str,
        format: str,
        content: str,
        source: CodeSource,
        status: str = "prototype",
        named_systems: list[str] | tuple[str, ...] = (),
        tags: list[str] | tuple[str, ...] = (),
        symbols: list[str] | tuple[str, ...] = (),
        runtime_adapter: str | None = None,
        parent_artifact_id: str | None = None,
        receipt_id: str | None = None,
    ) -> "CodeArtifact":
        source.validate()
        if status not in VALID_STATUSES:
            raise ValueError(f"Unsupported code artifact status: {status}")
        artifact = cls(
            schema_version=CODE_ARTIFACT_SCHEMA,
            artifact_id=new_id("code"),
            title=title.strip(),
            language=canonical_language(language),
            format=_normalize_id(format),
            content=content,
            source=source,
            status=status,
            created_at=utc_now(),
            content_hash=sha256_text(content),
            named_systems=tuple(named_systems),
            tags=tuple(tags),
            symbols=tuple(symbols),
            runtime_adapter=runtime_adapter,
            parent_artifact_id=parent_artifact_id,
            receipt_id=receipt_id,
        )
        artifact.validate()
        return artifact

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CodeArtifact":
        source = CodeSource(**dict(value["source"]))
        artifact = cls(
            schema_version=str(value["schema_version"]),
            artifact_id=str(value["artifact_id"]),
            title=str(value["title"]),
            language=str(value["language"]),
            format=str(value["format"]),
            content=str(value["content"]),
            source=source,
            status=str(value["status"]),
            created_at=str(value["created_at"]),
            content_hash=str(value["content_hash"]),
            named_systems=tuple(value.get("named_systems") or ()),
            tags=tuple(value.get("tags") or ()),
            symbols=tuple(value.get("symbols") or ()),
            runtime_adapter=value.get("runtime_adapter"),
            parent_artifact_id=value.get("parent_artifact_id"),
            receipt_id=value.get("receipt_id"),
        )
        artifact.validate()
        return artifact

    def validate(self) -> None:
        if self.schema_version != CODE_ARTIFACT_SCHEMA:
            raise ValueError("Unsupported code artifact schema")
        if not self.artifact_id or not self.title or not self.language or not self.format:
            raise ValueError("Code artifact identity, title, language, and format are required")
        self.source.validate()
        if self.status not in VALID_STATUSES:
            raise ValueError("Unsupported code artifact status")
        if self.content_hash != sha256_text(self.content):
            raise ValueError("Code artifact content hash mismatch")

    def to_dict(self) -> dict[str, Any]:
        value = {
            "schema_version": self.schema_version,
            "artifact_id": self.artifact_id,
            "title": self.title,
            "language": self.language,
            "format": self.format,
            "content": self.content,
            "source": self.source.to_dict(),
            "status": self.status,
            "created_at": self.created_at,
            "content_hash": self.content_hash,
            "named_systems": list(self.named_systems),
            "tags": list(self.tags),
            "symbols": list(self.symbols),
            "runtime_adapter": self.runtime_adapter,
            "parent_artifact_id": self.parent_artifact_id,
            "receipt_id": self.receipt_id,
        }
        return {key: item for key, item in value.items() if item is not None}


@dataclass(frozen=True)
class RecallHit:
    score: int
    artifact_id: str
    title: str
    language: str
    format: str
    source: dict[str, Any]
    content_hash: str
    receipt_id: str | None
    snippet: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CodeMemory:
    """Provenance-first, polyglot RAG0SHOT code memory.

    Recall and execution are intentionally separate. This component indexes and
    retrieves code; a runtime adapter and authority path are required elsewhere
    before recalled code may execute.
    """

    def __init__(self, store: GenesisStore):
        self.store = store

    def ingest(self, artifact: CodeArtifact) -> dict[str, Any]:
        artifact.validate()
        existing = self.find_exact(artifact.content_hash)
        if existing is not None:
            return existing
        payload = artifact.to_dict()
        self.store.put("code_artifact", artifact.artifact_id, artifact.created_at, payload)
        return payload

    def import_fenced_text(
        self,
        text: str,
        *,
        source: CodeSource,
        status: str = "prototype",
        named_systems: list[str] | tuple[str, ...] = (),
        tags: list[str] | tuple[str, ...] = (),
    ) -> list[dict[str, Any]]:
        artifacts: list[dict[str, Any]] = []
        for index, (language, content) in enumerate(extract_fenced_code(text), start=1):
            artifact = CodeArtifact.create(
                title=f"Recovered {language} block {index}",
                language=language,
                format=format_for_language(language),
                content=content,
                source=source,
                status=status,
                named_systems=named_systems,
                tags=tags,
            )
            artifacts.append(self.ingest(artifact))
        return artifacts

    def find_exact(self, reference: str) -> dict[str, Any] | None:
        for artifact in self.store.list_kind("code_artifact"):
            if reference in {artifact.get("artifact_id"), artifact.get("content_hash")}:
                return artifact
        return None

    def recall(
        self,
        query: str,
        *,
        languages: list[str] | tuple[str, ...] = (),
        named_systems: list[str] | tuple[str, ...] = (),
        source_kinds: list[str] | tuple[str, ...] = (),
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        query_tokens = _tokenize(query)
        language_filter = {canonical_language(value) for value in languages}
        system_filter = {value.casefold() for value in named_systems}
        source_filter = set(source_kinds)
        hits: list[RecallHit] = []

        for raw in self.store.list_kind("code_artifact"):
            artifact = CodeArtifact.from_dict(raw)
            if language_filter and artifact.language not in language_filter:
                continue
            if source_filter and artifact.source.kind not in source_filter:
                continue
            if system_filter and not any(system.casefold() in system_filter for system in artifact.named_systems):
                continue

            score = _score_artifact(artifact, query_tokens)
            if query_tokens and score == 0:
                continue
            hits.append(
                RecallHit(
                    score=score,
                    artifact_id=artifact.artifact_id,
                    title=artifact.title,
                    language=artifact.language,
                    format=artifact.format,
                    source=artifact.source.to_dict(),
                    content_hash=artifact.content_hash,
                    receipt_id=artifact.receipt_id,
                    snippet=_select_snippet(artifact.content, query_tokens),
                )
            )

        hits.sort(key=lambda hit: (-hit.score, hit.artifact_id))
        return [hit.to_dict() for hit in hits[: max(1, limit)]]


def extract_fenced_code(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"```([^\n`]*)\n(.*?)\n```", re.DOTALL)
    blocks: list[tuple[str, str]] = []
    for match in pattern.finditer(text):
        hint = match.group(1).strip().split(maxsplit=1)[0] if match.group(1).strip() else "text"
        blocks.append((canonical_language(hint), match.group(2)))
    return blocks


def canonical_language(language: str) -> str:
    normalized = _normalize_id(language)
    aliases = {
        "rs": "rust",
        "py": "python",
        "c++": "cpp",
        "cc": "cpp",
        "cxx": "cpp",
        "kt": "kotlin",
        "kts": "kotlin",
        "ts": "typescript",
        "tsx": "typescript",
        "js": "javascript",
        "jsx": "javascript",
        "web3.js": "javascript",
        "c#": "csharp",
        "cs": "csharp",
        "sol": "solidity",
        "sh": "shell",
        "bash": "shell",
        "zsh": "shell",
        "yml": "yaml",
        "md": "markdown",
        "jsonschema": "json-schema",
        "json_schema": "json-schema",
        "emoji": "emoji-a++",
        "emoji-a-plus-plus": "emoji-a++",
        "tre": "tre-logic",
        "trelogic": "tre-logic",
        "tre_logic": "tre-logic",
    }
    return aliases.get(normalized, normalized or "text")


def format_for_language(language: str) -> str:
    language = canonical_language(language)
    if language == "json-schema":
        return "schema"
    if language == "json":
        return "data"
    if language in {"yaml", "toml"}:
        return "config"
    if language == "sql":
        return "query"
    if language == "markdown":
        return "documentation"
    if language in {"emoji-a++", "tre-logic"}:
        return "workflow"
    return "source"


def sha256_text(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def _normalize_id(value: str) -> str:
    return value.strip().lower().replace(" ", "-")


def _tokenize(value: str) -> list[str]:
    return [token.casefold() for token in re.findall(r"[A-Za-z0-9_+#-]{2,}", value)]


def _score_artifact(artifact: CodeArtifact, query_tokens: list[str]) -> int:
    if not query_tokens:
        return 1
    fields = {
        "content": artifact.content.casefold(),
        "title": artifact.title.casefold(),
        "language": artifact.language.casefold(),
        "format": artifact.format.casefold(),
        "tags": " ".join(artifact.tags).casefold(),
        "systems": " ".join(artifact.named_systems).casefold(),
        "symbols": " ".join(artifact.symbols).casefold(),
    }
    score = 0
    for token in query_tokens:
        score += 3 if token in fields["content"] else 0
        score += 6 if token in fields["title"] else 0
        score += 4 if token in fields["language"] or token in fields["format"] else 0
        score += 5 if token in fields["tags"] else 0
        score += 7 if token in fields["systems"] else 0
        score += 8 if token in fields["symbols"] else 0
    return score


def _select_snippet(content: str, query_tokens: list[str]) -> str:
    lines = content.splitlines()
    if not lines:
        return ""
    index = 0
    for candidate, line in enumerate(lines):
        lowered = line.casefold()
        if any(token in lowered for token in query_tokens):
            index = candidate
            break
    start = max(0, index - 1)
    end = min(len(lines), index + 2)
    return "\n".join(lines[start:end])

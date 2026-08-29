use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::{BufRead, BufReader, BufWriter, Write};
use std::path::Path;
use thiserror::Error;
use uuid::Uuid;

pub const CODE_ARTIFACT_SCHEMA: &str = "migi-code-artifact.v0";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum SourceKind {
    Chat,
    Log,
    Repository,
    File,
    Generated,
    External,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ArtifactStatus {
    Concept,
    Specification,
    Prototype,
    Executable,
    Tested,
    Deprecated,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CodeSource {
    pub kind: SourceKind,
    pub uri: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub path: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub revision: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub conversation_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CodeArtifact {
    pub schema_version: String,
    pub artifact_id: String,
    pub title: String,
    /// Open identifier such as rust, python, cpp, kotlin, typescript, solidity,
    /// sql, cobol, json-schema, yaml, emoji-a++, or tre-logic.
    pub language: String,
    /// source, schema, config, query, workflow, documentation, or another
    /// caller-defined format.
    pub format: String,
    pub content: String,
    pub source: CodeSource,
    pub status: ArtifactStatus,
    #[serde(default)]
    pub named_systems: Vec<String>,
    #[serde(default)]
    pub tags: Vec<String>,
    #[serde(default)]
    pub symbols: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_adapter: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub parent_artifact_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub receipt_id: Option<String>,
    pub created_at: DateTime<Utc>,
    pub content_hash: String,
}

impl CodeArtifact {
    pub fn new(
        title: impl Into<String>,
        language: impl Into<String>,
        format: impl Into<String>,
        content: impl Into<String>,
        source: CodeSource,
        status: ArtifactStatus,
    ) -> Self {
        let content = content.into();
        let language = language.into();
        let format = format.into();
        Self {
            schema_version: CODE_ARTIFACT_SCHEMA.into(),
            artifact_id: Uuid::new_v4().to_string(),
            title: title.into(),
            language: normalize_id(&language),
            format: normalize_id(&format),
            content_hash: sha256_text(&content),
            content,
            source,
            status,
            named_systems: Vec::new(),
            tags: Vec::new(),
            symbols: Vec::new(),
            runtime_adapter: None,
            parent_artifact_id: None,
            receipt_id: None,
            created_at: Utc::now(),
        }
    }

    pub fn verify_hash(&self) -> bool {
        self.content_hash == sha256_text(&self.content)
    }
}

#[derive(Debug, Clone, Default)]
pub struct RecallQuery {
    pub text: String,
    pub languages: Vec<String>,
    pub named_systems: Vec<String>,
    pub source_kinds: Vec<SourceKind>,
    pub limit: usize,
}

impl RecallQuery {
    pub fn text(text: impl Into<String>) -> Self {
        Self {
            text: text.into(),
            limit: 8,
            ..Self::default()
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RecallHit {
    pub score: u32,
    pub artifact_id: String,
    pub title: String,
    pub language: String,
    pub format: String,
    pub source: CodeSource,
    pub content_hash: String,
    pub receipt_id: Option<String>,
    pub snippet: String,
}

#[derive(Debug, Clone, Default)]
pub struct RecallIndex {
    artifacts: Vec<CodeArtifact>,
}

impl RecallIndex {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn len(&self) -> usize {
        self.artifacts.len()
    }

    pub fn is_empty(&self) -> bool {
        self.artifacts.is_empty()
    }

    pub fn artifacts(&self) -> &[CodeArtifact] {
        &self.artifacts
    }

    pub fn ingest(&mut self, artifact: CodeArtifact) -> Result<(), RecallError> {
        validate_artifact(&artifact)?;
        self.artifacts.push(artifact);
        Ok(())
    }

    /// Baseline RAG0SHOT recall: deterministic lexical + metadata retrieval.
    /// A vector/embedding retriever can be added later without changing the
    /// artifact/provenance contract.
    pub fn search(&self, query: &RecallQuery) -> Vec<RecallHit> {
        let query_tokens = tokenize(&query.text);
        let language_filters: Vec<String> = query.languages.iter().map(|v| normalize_id(v)).collect();
        let system_filters: Vec<String> = query.named_systems.iter().map(|v| v.to_ascii_lowercase()).collect();

        let mut hits: Vec<RecallHit> = self
            .artifacts
            .iter()
            .filter(|artifact| {
                (language_filters.is_empty() || language_filters.contains(&normalize_id(&artifact.language)))
                    && (query.source_kinds.is_empty() || query.source_kinds.contains(&artifact.source.kind))
                    && (system_filters.is_empty()
                        || system_filters.iter().any(|wanted| {
                            artifact.named_systems.iter().any(|s| s.eq_ignore_ascii_case(wanted))
                        }))
            })
            .filter_map(|artifact| {
                let score = score_artifact(artifact, &query_tokens);
                if score == 0 && !query_tokens.is_empty() {
                    return None;
                }
                Some(RecallHit {
                    score,
                    artifact_id: artifact.artifact_id.clone(),
                    title: artifact.title.clone(),
                    language: artifact.language.clone(),
                    format: artifact.format.clone(),
                    source: artifact.source.clone(),
                    content_hash: artifact.content_hash.clone(),
                    receipt_id: artifact.receipt_id.clone(),
                    snippet: select_snippet(&artifact.content, &query_tokens),
                })
            })
            .collect();

        hits.sort_by(|a, b| b.score.cmp(&a.score).then_with(|| a.artifact_id.cmp(&b.artifact_id)));
        hits.truncate(if query.limit == 0 { 8 } else { query.limit });
        hits
    }

    pub fn save_jsonl(&self, path: impl AsRef<Path>) -> Result<(), RecallError> {
        let file = File::create(path)?;
        let mut writer = BufWriter::new(file);
        for artifact in &self.artifacts {
            serde_json::to_writer(&mut writer, artifact)?;
            writer.write_all(b"\n")?;
        }
        writer.flush()?;
        Ok(())
    }

    pub fn load_jsonl(path: impl AsRef<Path>) -> Result<Self, RecallError> {
        let file = File::open(path)?;
        let reader = BufReader::new(file);
        let mut index = Self::new();
        for (line_number, line) in reader.lines().enumerate() {
            let line = line?;
            if line.trim().is_empty() {
                continue;
            }
            let artifact: CodeArtifact = serde_json::from_str(&line)
                .map_err(|source| RecallError::JsonLine { line: line_number + 1, source })?;
            index.ingest(artifact)?;
        }
        Ok(index)
    }
}

#[derive(Debug, Error)]
pub enum RecallError {
    #[error("unsupported code artifact schema: {0}")]
    UnsupportedSchema(String),
    #[error("required artifact field is empty: {0}")]
    EmptyField(&'static str),
    #[error("artifact content hash does not match content for {0}")]
    HashMismatch(String),
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("JSON error on line {line}: {source}")]
    JsonLine { line: usize, source: serde_json::Error },
}

pub fn validate_artifact(artifact: &CodeArtifact) -> Result<(), RecallError> {
    if artifact.schema_version != CODE_ARTIFACT_SCHEMA {
        return Err(RecallError::UnsupportedSchema(artifact.schema_version.clone()));
    }
    for (name, value) in [
        ("artifact_id", artifact.artifact_id.as_str()),
        ("title", artifact.title.as_str()),
        ("language", artifact.language.as_str()),
        ("format", artifact.format.as_str()),
        ("source.uri", artifact.source.uri.as_str()),
    ] {
        if value.trim().is_empty() {
            return Err(RecallError::EmptyField(name));
        }
    }
    if !artifact.verify_hash() {
        return Err(RecallError::HashMismatch(artifact.artifact_id.clone()));
    }
    Ok(())
}

pub fn sha256_text(content: &str) -> String {
    let digest = Sha256::digest(content.as_bytes());
    format!("sha256:{digest:x}")
}

fn normalize_id(value: &str) -> String {
    value.trim().to_ascii_lowercase().replace(' ', "-")
}

fn tokenize(value: &str) -> Vec<String> {
    value
        .split(|c: char| !(c.is_ascii_alphanumeric() || matches!(c, '_' | '+' | '#' | '-')))
        .filter(|token| token.len() > 1)
        .map(|token| token.to_ascii_lowercase())
        .collect()
}

fn score_artifact(artifact: &CodeArtifact, query_tokens: &[String]) -> u32 {
    if query_tokens.is_empty() {
        return 1;
    }

    let content = artifact.content.to_ascii_lowercase();
    let title = artifact.title.to_ascii_lowercase();
    let language = artifact.language.to_ascii_lowercase();
    let format = artifact.format.to_ascii_lowercase();
    let tags = artifact.tags.join(" ").to_ascii_lowercase();
    let systems = artifact.named_systems.join(" ").to_ascii_lowercase();
    let symbols = artifact.symbols.join(" ").to_ascii_lowercase();

    query_tokens.iter().fold(0u32, |score, token| {
        score
            + if content.contains(token) { 3 } else { 0 }
            + if title.contains(token) { 6 } else { 0 }
            + if language.contains(token) || format.contains(token) { 4 } else { 0 }
            + if tags.contains(token) { 5 } else { 0 }
            + if systems.contains(token) { 7 } else { 0 }
            + if symbols.contains(token) { 8 } else { 0 }
    })
}

fn select_snippet(content: &str, query_tokens: &[String]) -> String {
    let lines: Vec<&str> = content.lines().collect();
    if lines.is_empty() {
        return String::new();
    }

    let match_index = lines.iter().position(|line| {
        let lower = line.to_ascii_lowercase();
        query_tokens.iter().any(|token| lower.contains(token))
    });

    let index = match_index.unwrap_or(0);
    let start = index.saturating_sub(1);
    let end = (index + 2).min(lines.len());
    lines[start..end].join("\n")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn source(kind: SourceKind, uri: &str) -> CodeSource {
        CodeSource {
            kind,
            uri: uri.into(),
            path: None,
            revision: None,
            conversation_id: None,
            message_id: None,
        }
    }

    #[test]
    fn recalls_across_code_formats_with_provenance() {
        let mut index = RecallIndex::new();

        let mut rust = CodeArtifact::new(
            "MIGIReceipt issuer",
            "rust",
            "source",
            "pub fn issue_receipt() { /* provenance */ }",
            source(SourceKind::Repository, "github:QSTARMIGI/MIGI"),
            ArtifactStatus::Tested,
        );
        rust.named_systems.push("MIGIReceipt".into());
        rust.symbols.push("issue_receipt".into());
        index.ingest(rust).unwrap();

        let mut emoji = CodeArtifact::new(
            "Emoji A++ receipt workflow",
            "emoji-a++",
            "workflow",
            "📷 capture → 🧾 receipt → 🧠 analyze",
            source(SourceKind::Chat, "chat:migi-emoji-workflow"),
            ArtifactStatus::Specification,
        );
        emoji.named_systems.push("Emoji A++".into());
        emoji.tags.push("receipt".into());
        index.ingest(emoji).unwrap();

        let hits = index.search(&RecallQuery::text("receipt provenance"));
        assert_eq!(hits.len(), 2);
        assert!(hits.iter().all(|hit| hit.content_hash.starts_with("sha256:")));
        assert!(hits.iter().any(|hit| hit.source.kind == SourceKind::Chat));
        assert!(hits.iter().any(|hit| hit.source.kind == SourceKind::Repository));
    }

    #[test]
    fn can_filter_by_language_and_named_system() {
        let mut index = RecallIndex::new();
        let mut python = CodeArtifact::new(
            "RAG0SHOT Python prototype",
            "python",
            "source",
            "def recall(query): return query",
            source(SourceKind::Log, "log:rag0shot"),
            ArtifactStatus::Prototype,
        );
        python.named_systems.push("RAG0SHOT".into());
        index.ingest(python).unwrap();

        let query = RecallQuery {
            text: "recall".into(),
            languages: vec!["python".into()],
            named_systems: vec!["RAG0SHOT".into()],
            source_kinds: vec![SourceKind::Log],
            limit: 4,
        };
        let hits = index.search(&query);
        assert_eq!(hits.len(), 1);
        assert_eq!(hits[0].language, "python");
    }

    #[test]
    fn jsonl_round_trip_preserves_hash_and_source() {
        let mut index = RecallIndex::new();
        index
            .ingest(CodeArtifact::new(
                "CAN adapter sketch",
                "cpp",
                "source",
                "void on_can_frame() {}",
                source(SourceKind::File, "file:can-adapter.cpp"),
                ArtifactStatus::Prototype,
            ))
            .unwrap();

        let path = std::env::temp_dir().join(format!("migi-recall-{}.jsonl", Uuid::new_v4()));
        index.save_jsonl(&path).unwrap();
        let loaded = RecallIndex::load_jsonl(&path).unwrap();
        std::fs::remove_file(path).ok();

        assert_eq!(loaded.len(), 1);
        assert!(loaded.artifacts()[0].verify_hash());
        assert_eq!(loaded.artifacts()[0].source.kind, SourceKind::File);
    }
}

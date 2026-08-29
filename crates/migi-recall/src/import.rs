use crate::{ArtifactStatus, CodeArtifact, CodeSource};

#[derive(Debug, Clone)]
pub struct ImportContext {
    pub source: CodeSource,
    pub status: ArtifactStatus,
    pub named_systems: Vec<String>,
    pub tags: Vec<String>,
}

impl ImportContext {
    pub fn new(source: CodeSource, status: ArtifactStatus) -> Self {
        Self {
            source,
            status,
            named_systems: Vec::new(),
            tags: Vec::new(),
        }
    }
}

/// Extract Markdown-style fenced code blocks from chat exports, notes, logs,
/// or documentation without altering the code inside each fence.
///
/// The importer deliberately does not execute or "fix" recovered code. It
/// creates provenance-carrying CodeArtifact records that can be recalled,
/// compared, reviewed, and later routed to an approved runtime adapter.
pub fn extract_fenced_code(text: &str, context: &ImportContext) -> Vec<CodeArtifact> {
    let mut artifacts = Vec::new();
    let mut in_fence = false;
    let mut language = String::new();
    let mut buffer = String::new();
    let mut block_number = 0usize;

    for line in text.lines() {
        let trimmed = line.trim_start();
        if !in_fence {
            if let Some(rest) = trimmed.strip_prefix("```") {
                in_fence = true;
                language = canonical_language(rest.trim().split_whitespace().next().unwrap_or("text"));
                if language.is_empty() {
                    language = "text".into();
                }
                buffer.clear();
            }
            continue;
        }

        if trimmed.starts_with("```") {
            block_number += 1;
            let mut artifact = CodeArtifact::new(
                format!("Recovered {} block {}", language, block_number),
                language.clone(),
                format_for_language(&language),
                buffer.trim_end_matches('\n').to_string(),
                context.source.clone(),
                context.status.clone(),
            );
            artifact.named_systems = context.named_systems.clone();
            artifact.tags = context.tags.clone();
            artifacts.push(artifact);
            in_fence = false;
            language.clear();
            buffer.clear();
            continue;
        }

        buffer.push_str(line);
        buffer.push('\n');
    }

    artifacts
}

pub fn canonical_language(language: &str) -> String {
    let normalized = language.trim().to_ascii_lowercase();
    match normalized.as_str() {
        "rs" => "rust".into(),
        "py" => "python".into(),
        "c++" | "cc" | "cxx" => "cpp".into(),
        "kt" | "kts" => "kotlin".into(),
        "ts" | "tsx" => "typescript".into(),
        "js" | "jsx" | "web3.js" => "javascript".into(),
        "c#" | "cs" => "csharp".into(),
        "sol" => "solidity".into(),
        "sh" | "bash" | "zsh" => "shell".into(),
        "yml" => "yaml".into(),
        "md" => "markdown".into(),
        "jsonschema" | "json_schema" => "json-schema".into(),
        "emoji" | "emoji-a-plus-plus" | "emoji-a++" => "emoji-a++".into(),
        "tre" | "trelogic" | "tre_logic" | "tre-logic" => "tre-logic".into(),
        "" => "text".into(),
        other => other.replace(' ', "-"),
    }
}

pub fn format_for_language(language: &str) -> &'static str {
    match language {
        "json-schema" => "schema",
        "json" => "data",
        "yaml" | "toml" => "config",
        "sql" => "query",
        "markdown" => "documentation",
        "emoji-a++" | "tre-logic" => "workflow",
        _ => "source",
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{SourceKind};

    fn context() -> ImportContext {
        ImportContext::new(
            CodeSource {
                kind: SourceKind::Chat,
                uri: "chat:example".into(),
                path: None,
                revision: None,
                conversation_id: Some("conversation-1".into()),
                message_id: Some("message-7".into()),
            },
            ArtifactStatus::Prototype,
        )
    }

    #[test]
    fn extracts_multiple_languages_without_rewriting_code() {
        let text = r#"
Discussion before code.

```python
def recall(query):
    return query
```

```c++
void on_can_frame() {}
```
"#;

        let artifacts = extract_fenced_code(text, &context());
        assert_eq!(artifacts.len(), 2);
        assert_eq!(artifacts[0].language, "python");
        assert_eq!(artifacts[0].content, "def recall(query):\n    return query");
        assert_eq!(artifacts[1].language, "cpp");
        assert_eq!(artifacts[1].content, "void on_can_frame() {}");
        assert!(artifacts.iter().all(|artifact| artifact.verify_hash()));
    }

    #[test]
    fn maps_symbolic_and_schema_formats() {
        assert_eq!(canonical_language("emoji-a++"), "emoji-a++");
        assert_eq!(format_for_language("emoji-a++"), "workflow");
        assert_eq!(canonical_language("jsonschema"), "json-schema");
        assert_eq!(format_for_language("json-schema"), "schema");
    }
}

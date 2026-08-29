use migi_recall::import::{extract_fenced_code, ImportContext};
use migi_recall::{ArtifactStatus, CodeSource, RecallIndex, RecallQuery, SourceKind};
use std::env;
use std::error::Error;
use std::fs;

fn main() {
    if let Err(error) = run() {
        eprintln!("migi-recall error: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn Error>> {
    let args: Vec<String> = env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("import") => import_command(&args[2..]),
        Some("search") => search_command(&args[2..]),
        Some("verify") => verify_command(&args[2..]),
        _ => {
            print_usage();
            Ok(())
        }
    }
}

fn import_command(args: &[String]) -> Result<(), Box<dyn Error>> {
    if args.len() < 4 {
        return Err("usage: migi-recall import <input.md> <output.jsonl> <source-kind> <source-uri> [status]".into());
    }

    let input_path = &args[0];
    let output_path = &args[1];
    let source_kind = parse_source_kind(&args[2])?;
    let source_uri = args[3].clone();
    let status = args
        .get(4)
        .map(|value| parse_status(value))
        .transpose()?
        .unwrap_or(ArtifactStatus::Prototype);

    let text = fs::read_to_string(input_path)?;
    let source = CodeSource {
        kind: source_kind,
        uri: source_uri,
        path: Some(input_path.clone()),
        revision: None,
        conversation_id: None,
        message_id: None,
    };
    let context = ImportContext::new(source, status);
    let artifacts = extract_fenced_code(&text, &context);

    let mut index = RecallIndex::new();
    for artifact in artifacts {
        index.ingest(artifact)?;
    }
    index.save_jsonl(output_path)?;
    println!("indexed {} code artifacts into {}", index.len(), output_path);
    Ok(())
}

fn search_command(args: &[String]) -> Result<(), Box<dyn Error>> {
    if args.len() < 2 {
        return Err("usage: migi-recall search <index.jsonl> <query...>".into());
    }
    let index = RecallIndex::load_jsonl(&args[0])?;
    let query_text = args[1..].join(" ");
    let hits = index.search(&RecallQuery::text(query_text));
    println!("{}", serde_json::to_string_pretty(&hits)?);
    Ok(())
}

fn verify_command(args: &[String]) -> Result<(), Box<dyn Error>> {
    if args.len() != 1 {
        return Err("usage: migi-recall verify <index.jsonl>".into());
    }
    let index = RecallIndex::load_jsonl(&args[0])?;
    println!("verified {} code artifacts", index.len());
    Ok(())
}

fn parse_source_kind(value: &str) -> Result<SourceKind, Box<dyn Error>> {
    match value.to_ascii_lowercase().as_str() {
        "chat" => Ok(SourceKind::Chat),
        "log" => Ok(SourceKind::Log),
        "repository" | "repo" => Ok(SourceKind::Repository),
        "file" => Ok(SourceKind::File),
        "generated" => Ok(SourceKind::Generated),
        "external" => Ok(SourceKind::External),
        other => Err(format!("unknown source kind: {other}").into()),
    }
}

fn parse_status(value: &str) -> Result<ArtifactStatus, Box<dyn Error>> {
    match value.to_ascii_lowercase().as_str() {
        "concept" => Ok(ArtifactStatus::Concept),
        "specification" | "spec" => Ok(ArtifactStatus::Specification),
        "prototype" => Ok(ArtifactStatus::Prototype),
        "executable" => Ok(ArtifactStatus::Executable),
        "tested" => Ok(ArtifactStatus::Tested),
        "deprecated" => Ok(ArtifactStatus::Deprecated),
        other => Err(format!("unknown artifact status: {other}").into()),
    }
}

fn print_usage() {
    eprintln!(
        "MIGI RAG0SHOT code recall\n\n\
         Commands:\n\
           migi-recall import <input.md> <output.jsonl> <source-kind> <source-uri> [status]\n\
           migi-recall search <index.jsonl> <query...>\n\
           migi-recall verify <index.jsonl>\n\n\
         source-kind: chat | log | repository | file | generated | external\n\
         status: concept | specification | prototype | executable | tested | deprecated"
    );
}

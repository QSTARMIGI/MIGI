from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .code_memory import CodeMemory, CodeSource
from .genesis import GenesisNode


class ExecuteRequest(BaseModel):
    action: str = Field(default="artifact.inspect")
    target: str
    actor_id: str = "local-user"
    consent_scope: str = "local.read"


class CodeImportRequest(BaseModel):
    text: str
    source_kind: str = "chat"
    source_uri: str
    status: str = "prototype"
    named_systems: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    path: str | None = None
    revision: str | None = None
    conversation_id: str | None = None
    message_id: str | None = None


DB_PATH = os.environ.get("MIGI_DB_PATH", ".migi/genesis.db")
ALLOWED_ROOT = Path(os.environ.get("MIGI_ALLOWED_ROOT", Path.cwd())).expanduser().resolve()
node = GenesisNode(DB_PATH, allowed_roots=[ALLOWED_ROOT])
code_memory = CodeMemory(node.store)
app = FastAPI(title="MIGI Genesis Node", version=node.VERSION)


@app.get("/status")
def status():
    value = node.status()
    capabilities = list(value.get("capabilities", []))
    capabilities.extend(["code.import", "code.recall", "code.find"])
    value["capabilities"] = sorted(set(capabilities))
    return value


@app.post("/execute")
def execute(request: ExecuteRequest):
    if request.action != "artifact.inspect":
        raise HTTPException(status_code=400, detail="This endpoint currently supports artifact.inspect only")
    return node.inspect_artifact(
        request.target,
        actor_id=request.actor_id,
        consent_scope=request.consent_scope,
    )


@app.get("/receipts")
def receipts():
    return {"chain": node.store.verify_chain(), "receipts": node.store.receipts()}


@app.get("/recall/{reference}")
def recall(reference: str):
    result = node.recall_artifact(reference)
    if result is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return result


@app.post("/code/import")
def import_code(request: CodeImportRequest):
    source = CodeSource(
        kind=request.source_kind,
        uri=request.source_uri,
        path=request.path,
        revision=request.revision,
        conversation_id=request.conversation_id,
        message_id=request.message_id,
    )
    try:
        artifacts = code_memory.import_fenced_text(
            request.text,
            source=source,
            status=request.status,
            named_systems=request.named_systems,
            tags=request.tags,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"count": len(artifacts), "artifacts": artifacts}


@app.get("/code/recall")
def recall_code(
    q: str = Query(..., min_length=1),
    language: list[str] = Query(default=[]),
    system: list[str] = Query(default=[]),
    source_kind: list[str] = Query(default=[]),
    limit: int = Query(default=8, ge=1, le=100),
):
    return {
        "query": q,
        "hits": code_memory.recall(
            q,
            languages=language,
            named_systems=system,
            source_kinds=source_kind,
            limit=limit,
        ),
    }


@app.get("/code/find/{reference}")
def find_code(reference: str):
    result = code_memory.find_exact(reference)
    if result is None:
        raise HTTPException(status_code=404, detail="Code artifact not found")
    return result

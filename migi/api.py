from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .genesis import GenesisNode


class ExecuteRequest(BaseModel):
    action: str = Field(default="artifact.inspect")
    target: str
    actor_id: str = "local-user"
    consent_scope: str = "local.read"


DB_PATH = os.environ.get("MIGI_DB_PATH", ".migi/genesis.db")
ALLOWED_ROOT = Path(os.environ.get("MIGI_ALLOWED_ROOT", Path.cwd())).expanduser().resolve()
node = GenesisNode(DB_PATH, allowed_roots=[ALLOWED_ROOT])
app = FastAPI(title="MIGI Genesis Node", version=node.VERSION)


@app.get("/status")
def status():
    return node.status()


@app.post("/execute")
def execute(request: ExecuteRequest):
    if request.action != "artifact.inspect":
        raise HTTPException(status_code=400, detail="Genesis v0.1 only supports artifact.inspect")
    result = node.inspect_artifact(
        request.target,
        actor_id=request.actor_id,
        consent_scope=request.consent_scope,
    )
    return result


@app.get("/receipts")
def receipts():
    return {"chain": node.store.verify_chain(), "receipts": node.store.receipts()}


@app.get("/recall/{reference}")
def recall(reference: str):
    result = node.recall_artifact(reference)
    if result is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return result

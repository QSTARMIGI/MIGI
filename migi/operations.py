"""MIGI Atomic Operation Protocol (AOP-001).

AOP stages a complete operation envelope before opening the storage transaction.
The storage layer then serializes receipt-head selection and commits every
operation object, content blob, and receipt as one SQLite transaction.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable, Protocol
from uuid import uuid4

from .models import MIGIReceipt


class AtomicStore(Protocol):
    def commit_operation(
        self,
        receipt: MIGIReceipt,
        objects: list[tuple[str, str, str, dict[str, Any]]],
        blobs: list[bytes] | None = None,
    ) -> tuple[MIGIReceipt, str]: ...


@dataclass(frozen=True)
class OperationObject:
    kind: str
    object_id: str
    created_at: str
    payload: dict[str, Any]

    def as_storage_tuple(self) -> tuple[str, str, str, dict[str, Any]]:
        if not self.kind or not self.object_id or not self.created_at:
            raise ValueError("operation_object_identity_required")
        return self.kind, self.object_id, self.created_at, self.payload


@dataclass(frozen=True)
class AtomicOperation:
    """A fully staged operation. Construct it before calling commit()."""

    receipt: MIGIReceipt
    objects: tuple[OperationObject, ...]
    blobs: tuple[bytes, ...] = ()
    operation_id: str = ""

    def __post_init__(self) -> None:
        if not self.operation_id:
            object.__setattr__(self, "operation_id", f"op_{uuid4().hex}")
        if not self.objects:
            raise ValueError("atomic_operation_requires_evidence_objects")
        ids = [(item.kind, item.object_id) for item in self.objects]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate_operation_object")
        for item in self.objects:
            item.as_storage_tuple()
        if "operation_id" in self.receipt.metadata:
            raise ValueError("operation_id_metadata_is_reserved")

    def commit(self, store: AtomicStore) -> tuple[MIGIReceipt, str]:
        """Commit all staged evidence or raise without returning a receipt.

        The store owns transaction boundaries, receipt-head selection, and
        rollback. Callers must retry the complete operation, never just the
        receipt append, after a busy/lock failure.
        """
        receipt = replace(
            self.receipt,
            metadata={**self.receipt.metadata, "operation_id": self.operation_id},
        )
        return store.commit_operation(
            receipt,
            [item.as_storage_tuple() for item in self.objects],
            list(self.blobs),
        )


def stage_operation(
    receipt: MIGIReceipt,
    objects: Iterable[OperationObject],
    *,
    blobs: Iterable[bytes] = (),
    operation_id: str = "",
) -> AtomicOperation:
    """Materialize iterables before transaction entry; no I/O occurs here."""
    return AtomicOperation(
        receipt=receipt,
        objects=tuple(objects),
        blobs=tuple(blobs),
        operation_id=operation_id,
    )

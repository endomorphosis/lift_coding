#!/usr/bin/env python3
"""Bounded neural tape: the TypeSafe context window.

A ring of cells. The head is the current theorem/node. TypeSafe reads a
window around the head, not the whole memory file. Child RETURN splices a
cell onto the parent tape. Jev does not write Lean. Never docker0.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

TAPE_N = 64
WINDOW = 7


def _cell(
    *,
    kind: str,
    payload: Any,
    energy: float = 0.5,
    ptr: str = "",
    parent_frame: str = "",
    tokens: int = 0,
    theorem_ok: Optional[bool] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "kind": str(kind),
        "payload": payload,
        "energy": float(energy),
        "ptr": str(ptr or ""),
        "parent_frame": str(parent_frame or ""),
        "tokens": int(tokens or 0),
        "theorem_ok": theorem_ok,
    }
    if extra:
        row.update(dict(extra))
    return row


class Tape:
    """Ring tape with a moving head."""

    def __init__(self, *, cells: Optional[list[dict[str, Any]]] = None, head: int = 0) -> None:
        self.cells: list[dict[str, Any]] = list(cells or [])
        self.head = int(head) if self.cells else 0
        self._trim()

    def _trim(self) -> None:
        overflow = len(self.cells) - TAPE_N
        if overflow > 0:
            self.cells = self.cells[overflow:]
            self.head = max(0, self.head - overflow)
        if self.cells:
            self.head = min(self.head, len(self.cells) - 1)

    def write(
        self,
        kind: str,
        payload: Any = None,
        *,
        energy: float = 0.5,
        ptr: str = "",
        parent_frame: str = "",
        tokens: int = 0,
        theorem_ok: Optional[bool] = None,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        cell = _cell(
            kind=kind,
            payload=payload,
            energy=energy,
            ptr=ptr,
            parent_frame=parent_frame,
            tokens=tokens,
            theorem_ok=theorem_ok,
            extra=extra,
        )
        self.cells.append(cell)
        self.head = len(self.cells) - 1
        self._trim()
        return cell

    def window(self, width: int = WINDOW) -> list[dict[str, Any]]:
        if not self.cells:
            return []
        lo = max(0, self.head - int(width))
        hi = min(len(self.cells), self.head + int(width) + 1)
        return list(self.cells[lo:hi])

    def splice_return(
        self,
        payload: Mapping[str, Any],
        *,
        ptr: str = "",
        parent_frame: str = "",
    ) -> dict[str, Any]:
        """Inject a child evaluation onto the parent tape."""

        energy = float(payload.get("energy") or 0.5)
        if payload.get("theorem_ok") is True:
            energy = max(energy, 0.7)
        if payload.get("theorem_ok") is False:
            energy = min(energy, 0.3)
        return self.write(
            "return",
            {
                "observations": payload.get("observations") or {},
                "tactics_head": str(payload.get("tactics") or "")[:240],
                "n_steps": payload.get("n_steps"),
                "ok": payload.get("ok", True),
            },
            energy=energy,
            ptr=ptr,
            parent_frame=parent_frame,
            tokens=int(payload.get("tokens") or 0),
            theorem_ok=payload.get("theorem_ok") if "theorem_ok" in payload else None,
            extra={"injected": True, "node": payload.get("node")},
        )

    def to_dict(self) -> dict[str, Any]:
        return {"cells": list(self.cells[-TAPE_N:]), "head": self.head, "n": len(self.cells)}

    @classmethod
    def from_memory(cls, memory: Optional[Mapping[str, Any]]) -> "Tape":
        raw = (memory or {}).get("tape") or {}
        cells = list(raw.get("cells") or [])
        head = int(raw.get("head") or max(0, len(cells) - 1))
        return cls(cells=cells, head=head)

    def persist(self, memory: dict[str, Any]) -> None:
        memory["tape"] = self.to_dict()

    def read(self) -> Optional[dict[str, Any]]:
        if not self.cells:
            return None
        return self.cells[self.head]

    def seek(self, index: int) -> Optional[dict[str, Any]]:
        if not self.cells:
            return None
        self.head = max(0, min(int(index), len(self.cells) - 1))
        return self.read()

    def cells_for_frame(self, frame_id: str) -> list[dict[str, Any]]:
        fid = str(frame_id or "")
        return [cell for cell in self.cells if str(cell.get("parent_frame") or "") == fid]

    def populate(
        self,
        *,
        stack: Any = None,
        tactics: str = "",
        problem: str = "",
        observations: Optional[Mapping[str, Any]] = None,
        ptr: str = "",
    ) -> dict[str, Any]:
        """Write the current stack frame's args onto the tape for TypeSafe."""

        frame = stack.top() if stack is not None and hasattr(stack, "top") else None
        locals_ = dict((frame or {}).get("locals") or {})
        if tactics:
            locals_["tactics"] = tactics
        if problem:
            locals_["problem"] = problem
        cell = self.write(
            "args",
            {
                "locals": {k: locals_[k] for k in list(locals_)[:12]},
                "observations_keys": sorted((observations or {}).keys())[:16],
            },
            ptr=ptr or str((frame or {}).get("ptr") or ""),
            parent_frame=str((frame or {}).get("frame_id") or ""),
            extra={"node": (frame or {}).get("node")},
        )
        return cell


def populate_tape(
    tape: Tape,
    stack: Any,
    *,
    tactics: str = "",
    problem: str = "",
    observations: Optional[Mapping[str, Any]] = None,
    ptr: str = "",
) -> dict[str, Any]:
    return tape.populate(
        stack=stack,
        tactics=tactics,
        problem=problem,
        observations=observations,
        ptr=ptr,
    )

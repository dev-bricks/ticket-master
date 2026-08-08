r"""
ticket_mover.py — Fail-closed move for ticket files between lifecycle folders.

Ticket T-20260808-03: no code path existed for moving a ticket between
status folders (INBOX/ACTIONABLE/QUEUED/.../SOLVED). Moves happened by hand
(an agent reading a file's content and writing it to the new location, or a
plain shell `mv`), with no check whether the destination already held an
unrelated ticket under the same ID. On 2026-08-08 that silently destroyed a
ticket that had lived in SOLVED/ since 2026-08-01: the overwriting write
looked completely normal on readback, so the loss was invisible until file
counts were compared.

move_ticket() closes that gap structurally, not procedurally: it refuses to
write over an existing destination, using the same atomic-exclusive-create
primitive already proven in ticket_writer.create() (`os.O_EXCL`), so the
result does not depend on whoever calls it remembering to check first.

Same-host multi-agent races (the actual failure mode here) are a purely
local filesystem question: two agents on one host both hit the same local
OneDrive-mirrored folder in real time, so O_EXCL's atomicity is authoritative
immediately — no cloud sync delay is involved. Sync delay only matters for
cross-host collisions, which the existing <HOST> filename suffix already
handles separately.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path


class TicketCollisionError(RuntimeError):
    """Raised when a move target already holds a (different) ticket file."""


def move_ticket(source: Path | str, dest_dir: Path | str) -> Path:
    """Move a ticket file into dest_dir under its current filename.

    Fails closed: if dest_dir already contains a file with that name, nothing
    is written and nothing is deleted — TicketCollisionError is raised and
    both the source and the pre-existing destination file are left exactly
    as they were. The destination is created via O_CREAT|O_EXCL (atomic on
    both POSIX and Windows), so a second caller racing for the same
    destination name always loses cleanly instead of overwriting the winner.

    The source is only deleted after the destination write is confirmed via
    a byte-for-byte readback AND the source is re-read and confirmed
    unchanged since the copy was made (guards against a foreign writer
    editing the ticket while the move is in flight — the move then aborts
    with both copies intact rather than deleting a stale source under a
    changed original).
    """
    source = Path(source)
    dest_dir = Path(dest_dir)
    if not source.is_file():
        raise FileNotFoundError(f"move source does not exist or is not a file: {source}")

    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / source.name
    if target.exists():
        raise TicketCollisionError(
            f"move target already exists, refusing to overwrite: {target}"
        )

    data = source.read_bytes()
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
    try:
        fd = os.open(str(target), flags, 0o644)
    except FileExistsError as exc:
        # Lost the race between the exists() check above and this open():
        # another mover won in between. Fail closed either way.
        raise TicketCollisionError(
            f"move target already exists, refusing to overwrite: {target}"
        ) from exc

    written_ok = False
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        if target.read_bytes() != data:
            raise RuntimeError(f"post-write verification failed for {target}")
        if source.read_bytes() != data:
            raise RuntimeError(
                f"source changed during move, aborting without deleting it: {source}"
            )
        written_ok = True
    finally:
        if not written_ok:
            # Partial/failed write or verification mismatch: remove the
            # half-written destination so a retry does not itself trip the
            # collision guard, and leave the source untouched either way.
            with contextlib.suppress(FileNotFoundError, OSError):
                target.unlink()

    source.unlink()
    return target


def _cli(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="ticket_mover",
        description="Fail-closed move of a single ticket file into a lifecycle folder.",
    )
    parser.add_argument("source", help="Path to the ticket file to move.")
    parser.add_argument("dest_dir", help="Destination lifecycle folder (e.g. .../SOLVED).")
    args = parser.parse_args(argv)
    try:
        target = move_ticket(args.source, args.dest_dir)
    except (TicketCollisionError, FileNotFoundError, RuntimeError) as exc:
        print(f"REFUSED: {exc}")
        return 1
    print(f"MOVED: {target}")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(_cli(sys.argv[1:]))

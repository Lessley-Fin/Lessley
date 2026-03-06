from __future__ import annotations

import asyncio
import sys

from hot.import_businesses import run as shared_run


def _ensure_default_club() -> None:
    has_club_flag = any(arg == "--club" or arg.startswith("--club=") for arg in sys.argv[1:])
    if not has_club_flag:
        sys.argv.extend(["--club", "behatsdaa"])


if __name__ == "__main__":
    _ensure_default_club()
    asyncio.run(shared_run())


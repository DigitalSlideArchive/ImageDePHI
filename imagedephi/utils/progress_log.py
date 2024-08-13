from pathlib import Path
import queue

_progress_queue: queue.Queue[tuple] = queue.Queue(-1)


def push_progress(count: int, max: int, redact_dir: Path) -> None:
    _progress_queue.put_nowait((count, max, redact_dir))


def get_next_progress_message() -> tuple | None:
    try:
        record = _progress_queue.get_nowait()
    except queue.Empty:
        return None
    else:
        # return record.message
        return record

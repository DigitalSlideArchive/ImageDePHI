# import logging
# import logging.handlers
import queue

# _progress_logger = logging.getLogger('progress')
# _progress_queue: queue.Queue[logging.LogRecord] = queue.Queue(-1)
_progress_queue: queue.Queue[tuple] = queue.Queue(-1)

# _queue_handler = logging.handlers.QueueHandler(_progress_queue)
# _progress_logger.addHandler(_queue_handler)


def push_progress(file_name: str, count: int, max: int) -> None:
    # _progress_logger.info("Redacting %s. Image %d of %d", file_name, count, max)
    _progress_queue.put_nowait((count, max))


def get_next_progress_message() -> tuple | None:
    try:
        record = _progress_queue.get_nowait()
    except queue.Empty:
        return None
    else:
        # return record.message
        return record

import ctypes
import sys


def launched_from_frozen_binary() -> bool:
    """Return whether the current program was launched within a frozen binary."""
    # https://pyinstaller.org/en/stable/runtime-information.html#run-time-information
    return getattr(sys, "frozen", False)


def launched_from_windows_explorer() -> bool:
    """Return whether the current program was launched directly from the Windows Explorer."""
    # Using "platform.system()" is preferred: https://stackoverflow.com/a/58071295
    # However, this is not recognised by Mypy yet: https://github.com/python/mypy/issues/8166
    if sys.platform == "win32":
        # See https://devblogs.microsoft.com/oldnewthing/20160125-00/?p=92922 for this algorithm.
        # Contradicting the blog, the API docs
        # https://learn.microsoft.com/en-us/windows/console/getconsoleprocesslist
        # indicate that the "process_list" array may not be null.
        # Also "process_list" must have a size larger than 0, but its full content isn't needed.
        process_list_size = 1
        # Array elements should be DWORD, which is a uint
        process_list = (ctypes.c_uint * process_list_size)()
        process_count: int = ctypes.windll.kernel32.GetConsoleProcessList(
            process_list, process_list_size
        )
        if process_count == 0:
            # TODO: Log this internally
            raise OSError("Could not detect Windows console.")
        # If frozen, the Pyinstaller bootloader is also running in this console:
        # https://pyinstaller.org/en/stable/advanced-topics.html#the-bootstrap-process-in-detail
        expected_solo_process_count = 2 if launched_from_frozen_binary() else 1
        return process_count == expected_solo_process_count
    else:
        return False

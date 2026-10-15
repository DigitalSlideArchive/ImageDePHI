import multiprocessing

if __name__ == "__main__":
    # Required for frozen (PyInstaller) builds on platforms that use the "spawn"
    # start method (macOS, Windows). Without it, helper processes (e.g. the
    # multiprocessing resource tracker started by tqdm's lock) re-run the full
    # entry point. This must run before importing anything heavy.
    multiprocessing.freeze_support()

    from imagedephi import main

    main.imagedephi()

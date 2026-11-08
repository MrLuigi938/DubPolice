"""Entry point of DubPolice.exe: opens the window, or does the conversion when called with --engine."""
import multiprocessing
import sys


def main():
    multiprocessing.freeze_support()
    if "--engine" in sys.argv:
        sys.argv.remove("--engine")
        import sammax_de

        try:
            sammax_de.main()
        except SystemExit as stop:
            if isinstance(stop.code, str):
                print(stop.code, flush=True)
                sys.exit(1)
            raise
        except Exception:  # noqa: BLE001 - the window shows the log; a crash dialog would only block it
            import traceback

            traceback.print_exc()
            sys.stdout.flush()
            sys.exit(1)
    else:
        import gui

        gui.run()


if __name__ == "__main__":
    main()

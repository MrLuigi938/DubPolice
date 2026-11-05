"""Entry point of SamMaxDeutsch.exe: opens the window, or does the conversion when called with --engine."""
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
    else:
        import gui

        gui.run()


if __name__ == "__main__":
    main()

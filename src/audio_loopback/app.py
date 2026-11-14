import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from .gui import MainWindow


def main():
    application = QApplication(sys.argv)
    application.setApplicationName("Audio Loopback Tester")
    application.setOrganizationName("AudioLoopback")
    if "--smoke-test" in sys.argv:
        from .smoke import run_smoke

        position = sys.argv.index("--smoke-test")
        report = (
            sys.argv[position + 1]
            if position + 1 < len(sys.argv)
            else "smoke-report.json"
        )
        return run_smoke(application, report)
    try:
        window = MainWindow()
    except Exception as error:
        QMessageBox.critical(None, "Unable to launch", str(error))
        return 1
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())

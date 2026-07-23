import sys
import signal
import threading

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from g2b_alert.app import Application
from g2b_alert.model.logging_setup import setup_logger


def main():
    logger = setup_logger()
    qt_app = None
    application = None
    interrupt_timer = None

    def report_thread_exception(args):
        logger.critical(
            "Unhandled background thread error: %s",
            args.thread.name if args.thread else "unknown",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    try:
        qt_app = QApplication.instance() or QApplication(sys.argv)
        qt_app.setApplicationName("g2bAlert")
        qt_app.setOrganizationName("g2bAlert")
        threading.excepthook = report_thread_exception
        application = Application(qt_app)

        def handle_console_interrupt(_signal_number, _frame):
            logger.info("Console interrupt requested.")
            if application is not None and not application.view.closing:
                application.close()
            else:
                qt_app.quit()

        signal.signal(signal.SIGINT, handle_console_interrupt)
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, handle_console_interrupt)

        # Let Python service console signals while Qt owns the main event loop.
        interrupt_timer = QTimer()
        interrupt_timer.timeout.connect(lambda: None)
        interrupt_timer.start(200)
        exit_code = qt_app.exec()
        if application is not None and not application.view.closing:
            logger.critical("Application main loop ended without a normal close request.")
        return exit_code
    except BaseException:
        logger.critical("Application startup or main loop terminated unexpectedly.", exc_info=True)
        raise
    finally:
        logger.info("Application main loop ended.")


if __name__ == "__main__":
    main()

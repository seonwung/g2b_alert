import tkinter as tk
import threading

from g2b_alert.app import Application
from g2b_alert.model.logging_setup import setup_logger


def main():
    logger = setup_logger()
    root = None
    application = None

    def report_tk_exception(exc_type, value, traceback):
        logger.critical(
            "Unhandled Tkinter callback error.",
            exc_info=(exc_type, value, traceback),
        )

    def report_thread_exception(args):
        logger.critical(
            "Unhandled background thread error: %s",
            args.thread.name if args.thread else "unknown",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    try:
        root = tk.Tk()
        root.report_callback_exception = report_tk_exception
        threading.excepthook = report_thread_exception
        application = Application(root)
        root.mainloop()
        if application is not None and not application.view.closing:
            logger.critical("Application main loop ended without a normal close request.")
    except BaseException:
        logger.critical("Application startup or main loop terminated unexpectedly.", exc_info=True)
        raise
    finally:
        logger.info("Application main loop ended.")


if __name__ == "__main__":
    main()

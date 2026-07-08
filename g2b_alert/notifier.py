try:
    from winotify import Notification, audio
except ImportError:
    Notification = None
    audio = None


class WindowsNotifier:
    def __init__(self, app_id="\ub098\ub77c\uc7a5\ud130 \uacf5\uace0 \uc54c\ub9bc", logger=None):
        self.app_id = app_id
        self.logger = logger

    def send(self, title, message):
        if Notification is None:
            if self.logger:
                self.logger.warning("winotify is not installed. Windows notification skipped.")
            return

        toast = Notification(
            app_id=self.app_id,
            title=title,
            msg=message,
            duration="long",
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()

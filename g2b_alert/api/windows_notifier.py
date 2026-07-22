try:
    from winotify import Notification, audio
except ImportError:
    Notification = None
    audio = None


class WindowsNotifier:
    def __init__(self, app_id="나라장터 공고 알림", logger=None):
        self.app_id = app_id
        self.logger = logger

    def send(self, title, message):
        if Notification is None:
            if self.logger:
                self.logger.warning("winotify is not installed. Windows notification skipped.")
            return False

        try:
            toast = Notification(
                app_id=self.app_id,
                title=title,
                msg=message,
                duration="long",
            )
            toast.set_audio(audio.Default, loop=False)
            toast.show()
            return True
        except Exception:
            if self.logger:
                self.logger.exception("Windows notification failed.")
            return False

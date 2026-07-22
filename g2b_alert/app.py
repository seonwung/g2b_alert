"""Application composition entry used by the minimal top-level launcher."""

from .controller.app_controller import AppController
from .model.config import load_config
from .model.database import G2BDatabase
from .model.logging_setup import setup_logger
from .view.main_view import MainView


class Application(AppController):
    """Create shared dependencies, then hand them to the controller."""

    def __init__(self, root):
        super().__init__(
            root=root,
            logger=setup_logger(),
            config=load_config(),
            database=G2BDatabase(),
            view_factory=MainView,
        )

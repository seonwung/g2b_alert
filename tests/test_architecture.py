import ast
import inspect
import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from g2b_alert.api.bid_api import G2BClient
from g2b_alert.api.result_api import ResultApiService
from g2b_alert.app import Application
from g2b_alert.controller.app_controller import AppController
from g2b_alert.model.config import AppConfig
from g2b_alert.model.database import G2BDatabase
from g2b_alert.model.repositories.bid_repository import BidRepository
from g2b_alert.model.repositories.email_repository import EmailRepository
from g2b_alert.model.repositories.result_repository import ResultRepository
from g2b_alert.presentation.contracts import (
    AppViewProtocol,
    MainViewState,
    ViewActionsProtocol,
)
from g2b_alert.view.main_view import MainView
from g2b_alert.view.ui_dispatcher import UiDispatcher


class FakeRoot:
    def __init__(self):
        self.scheduled = []

    def after(self, _delay, callback):
        self.scheduled.append(callback)


class ArchitectureTest(unittest.TestCase):
    @staticmethod
    def _member_names_used(paths, owner_name):
        names = set()
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Attribute):
                    continue
                owner = node.value
                if (
                    isinstance(owner, ast.Attribute)
                    and isinstance(owner.value, ast.Name)
                    and owner.value.id == "self"
                    and owner.attr == owner_name
                ):
                    names.add(node.attr)
        return names

    def test_package_root_contains_only_composition_modules(self):
        package_root = Path(__file__).resolve().parents[1] / "g2b_alert"
        root_modules = {path.name for path in package_root.glob("*.py")}
        self.assertEqual({"__init__.py", "app.py"}, root_modules)

    def test_public_application_and_mvc_api_modules_are_importable(self):
        self.assertTrue(issubclass(Application, AppController))
        self.assertTrue(callable(G2BClient.fetch_bids))
        self.assertTrue(callable(ResultApiService.fetch_results))
        with tempfile.TemporaryDirectory() as temp_dir:
            database = G2BDatabase(Path(temp_dir) / "architecture.db")
            self.assertIsInstance(database.bids, BidRepository)
            self.assertIsInstance(database.results, ResultRepository)
            self.assertIsInstance(database.email, EmailRepository)

    def test_ui_dispatcher_queues_callbacks_until_main_thread_poll(self):
        root = FakeRoot()
        dispatcher = UiDispatcher(root)
        called = []
        dispatcher.post(lambda: called.append("done"))

        self.assertEqual([], called)
        root.scheduled.pop(0)()
        self.assertEqual(["done"], called)

        dispatcher.stop()

    def test_mvc_layers_do_not_import_forbidden_dependencies(self):
        package_root = Path(__file__).resolve().parents[1] / "g2b_alert"
        forbidden_by_layer = {
            "view": ("from ..model", "from ..api", "from ..controller"),
            "model": (
                "from ..api",
                "from ..view",
                "from ..controller",
                "import tkinter",
                "from tkinter",
                "import threading",
            ),
            "controller": ("import tkinter", "from tkinter", "from ..view"),
        }
        for layer, forbidden_imports in forbidden_by_layer.items():
            for path in (package_root / layer).rglob("*.py"):
                source = path.read_text(encoding="utf-8")
                for forbidden in forbidden_imports:
                    self.assertNotIn(forbidden, source, f"{path} imports forbidden dependency: {forbidden}")

    def test_controller_and_view_do_not_use_hidden_attribute_delegation(self):
        package_root = Path(__file__).resolve().parents[1] / "g2b_alert"
        for relative_path in ("controller/app_controller.py", "view/main_view.py"):
            source = (package_root / relative_path).read_text(encoding="utf-8")
            self.assertNotIn("def __getattr__", source)

    def test_controller_and_view_calls_are_covered_by_public_contracts(self):
        package_root = Path(__file__).resolve().parents[1] / "g2b_alert"
        controller_paths = list((package_root / "controller").glob("*.py"))
        view_paths = list((package_root / "view").glob("*.py"))
        view_members = {
            name for name, value in inspect.getmembers(AppViewProtocol, inspect.isfunction)
        }
        action_members = {
            name
            for name, value in inspect.getmembers(ViewActionsProtocol, inspect.isfunction)
        }

        self.assertEqual(
            set(),
            self._member_names_used(controller_paths, "view") - view_members,
        )
        self.assertEqual(
            set(),
            self._member_names_used(view_paths, "actions") - action_members,
        )

        tkinter_view_members = {
            name for name, value in inspect.getmembers(MainView, inspect.isfunction)
        }
        controller_members = {
            name for name, value in inspect.getmembers(AppController, inspect.isfunction)
        }
        self.assertEqual(set(), view_members - tkinter_view_members)
        self.assertEqual(set(), action_members - controller_members)

    def test_view_does_not_read_controller_or_model_configuration(self):
        package_root = Path(__file__).resolve().parents[1] / "g2b_alert"
        for path in (package_root / "view").glob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("self.config", source, str(path))
            self.assertNotIn("controller.config", source, str(path))
            self.assertNotIn("controller.view", source, str(path))

    def test_legacy_json_state_files_are_not_referenced(self):
        package_root = Path(__file__).resolve().parents[1] / "g2b_alert"
        source = "\n".join(
            path.read_text(encoding="utf-8") for path in package_root.rglob("*.py")
        )
        self.assertNotIn("seen_bids.json", source)
        self.assertNotIn("state.json", source)

    def test_view_factory_finishes_before_controller_uses_the_view(self):
        class FakeView:
            def __init__(self, initial_state):
                self.initial_state = initial_state
                self.rows = []

            def set_close_handler(self, callback):
                self.close_handler = callback

            def update_running_ui(self, is_running):
                self.is_running = is_running

            def post(self, callback):
                callback()

            def get_saved_search_text(self):
                return ""

            def get_saved_filters(self):
                return {}

            def get_saved_sort(self):
                return "last_check", True

            def render_saved_bids(self, rows):
                self.rows = list(rows)

            def set_saved_monitor_status(self, text):
                self.saved_monitor_status = text

            def get_result_interval_text(self):
                return self.initial_state.result_interval

            def schedule(self, _delay_ms, _callback):
                pass

            def log(self, message):
                self.last_log = message

        with tempfile.TemporaryDirectory() as temp_dir:
            database = G2BDatabase(Path(temp_dir) / "architecture.db")
            factory_observation = {}

            def view_factory(_root, controller, initial_state):
                factory_observation["controller_had_view"] = hasattr(controller, "view")
                factory_observation["state"] = initial_state
                return FakeView(initial_state)

            # Exercise construction without starting a real delivery thread.
            with patch(
                "g2b_alert.controller.app_controller.EmailDeliveryWorker.start"
            ):
                controller = AppController(
                    root=object(),
                    logger=Mock(),
                    config=AppConfig(),
                    database=database,
                    view_factory=view_factory,
                )

            self.assertFalse(factory_observation["controller_had_view"])
            self.assertIsInstance(factory_observation["state"], MainViewState)
            self.assertIs(controller.view.initial_state, factory_observation["state"])
            self.assertEqual([], controller.view.rows)
            self.assertTrue(controller.view.saved_monitor_status)


if __name__ == "__main__":
    unittest.main()

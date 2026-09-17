"""Le constructeur de commandes et la configuration de la GUI."""

import tempfile
import unittest
from pathlib import Path

from butbutbut import gui


class TestGuiModel(unittest.TestCase):
    def test_wheel_deltas_never_disappear(self):
        self.assertEqual(gui.wheel_units(120), -3)
        self.assertEqual(gui.wheel_units(-120), 3)
        self.assertEqual(gui.wheel_units(1), -1)
        self.assertEqual(gui.wheel_units(-1), 1)
        self.assertEqual(gui.wheel_units(button=4), -3)
        self.assertEqual(gui.wheel_units(button=5), 3)

    def test_every_action_has_a_unique_name(self):
        names = [action.name for action in gui.ACTIONS]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(names), set(gui.ACTION_BY_NAME))

    def test_optional_value_follows_its_flag(self):
        self.assertEqual(
            gui.action_arguments(gui.ACTION_BY_NAME["next"], {"query": "om"}),
            ["--next", "om"])
        self.assertEqual(
            gui.action_arguments(gui.ACTION_BY_NAME["next"], {"query": ""}),
            ["--next"])

    def test_export_combines_format_and_period(self):
        values = {
            "format": "csv",
            "period": "Depuis une date",
            "since_date": "2026-09-01",
            "output_file": "buts.csv",
        }
        self.assertEqual(
            gui.action_arguments(gui.ACTION_BY_NAME["export"], values),
            ["--export", "csv", "--since", "2026-09-01"])

    def test_switches_only_emit_when_enabled(self):
        action = gui.ACTION_BY_NAME["check_update"]
        self.assertEqual(gui.action_arguments(action, {"dev": False}),
                         ["--check-update"])
        self.assertEqual(gui.action_arguments(action, {"dev": True}),
                         ["--check-update", "--dev"])

    def test_write_config_uses_its_file_as_config_path_in_the_launcher(self):
        action = gui.ACTION_BY_NAME["write_config"]
        self.assertEqual(
            gui.action_arguments(action, {"file": "butbutbut.conf"}),
            ["--write-config"])

    def test_settings_round_trip(self):
        # Un fichier direct plutot qu'un sous-dossier temporaire : les tests
        # tournent aussi dans des bacs a sable Windows qui interdisent parfois
        # l'heritage d'ACL sur un nouveau dossier.
        handle = tempfile.NamedTemporaryFile(
            dir=Path(__file__).parent, suffix=".conf", delete=False)
        handle.close()
        path = Path(handle.name)
        try:
            values = {item.name: item.default for item in gui.SETTINGS}
            values.update({
                "leagues": "l1,ucl",
                "teams": "om",
                "volume": "42",
                "speak": True,
                "no_sound": False,
            })
            path.write_text(gui.serialize_settings(values), encoding="utf-8")
            outcome = gui.config.read(path)
            self.assertFalse(outcome.warnings)
            self.assertEqual(outcome.values["leagues"], "l1,ucl")
            self.assertEqual(outcome.values["teams"], "om")
            self.assertEqual(outcome.values["volume"], 42)
            self.assertIs(outcome.values["speak"], True)
            self.assertIs(outcome.values["no_sound"], False)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

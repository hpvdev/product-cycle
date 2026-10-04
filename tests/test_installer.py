import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from product_cycle.contracts import WorkflowError
from product_cycle.installer import install_skills, update_skills, uninstall_skills
from product_cycle.cli import main
from product_cycle.store import Store


class SkillUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "project"
        self.project.mkdir()
        self.source = self.base / "product-cycle-analysis"
        self.source.mkdir()
        (self.source / "SKILL.md").write_text("Original instructions")
        self.destination = self.project / ".agents/skills"
        self.locations = patch("product_cycle.installer.skill_locations", return_value=(self.project, [self.source], self.destination))
        self.locations.start()
        self.addCleanup(self.locations.stop)

    def changed_bundle(self):
        (self.source / "SKILL.md").write_text("Updated instructions")
        (self.source / "reference.md").write_text("New reference")

    def test_preview_does_not_write_even_to_uninstalled_project(self):
        report = update_skills(self.project)
        self.assertFalse(report["applied"])
        self.assertEqual(report["skills"][0]["status"], "install")
        self.assertFalse((self.project / ".agents").exists())
        self.assertFalse((self.project / ".product-cycle").exists())

    def test_tracked_update_backs_up_old_files_and_is_idempotent(self):
        install_skills(self.project)
        old = self.destination / self.source.name
        self.changed_bundle()
        report = update_skills(self.project, apply=True)
        self.assertEqual((Path(report["backup"]) / self.source.name / "SKILL.md").read_text(), "Original instructions")
        self.assertEqual((old / "reference.md").read_text(), "New reference")
        self.assertEqual(update_skills(self.project)["skills"][0]["status"], "unchanged")
        self.assertIsNone(update_skills(self.project, apply=True)["backup"])

    def test_customization_requires_selected_override_and_is_preserved_in_backup(self):
        install_skills(self.project)
        target = self.destination / self.source.name
        (target / "SKILL.md").write_text("Project-specific instructions")
        (target / "notes.md").write_text("Project notes")
        self.changed_bundle()
        with self.assertRaises(WorkflowError):
            update_skills(self.project, apply=True)
        with self.assertRaises(WorkflowError):
            update_skills(self.project, apply=True, replace_customized=True)
        self.assertEqual((target / "SKILL.md").read_text(), "Project-specific instructions")
        report = update_skills(self.project, apply=True, selected=[self.source.name], replace_customized=True)
        backup = Path(report["backup"]) / self.source.name
        self.assertEqual((backup / "notes.md").read_text(), "Project notes")

    def test_legacy_unknown_version_is_not_silently_replaced(self):
        target = self.destination / self.source.name
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("Unknown old release")
        report = update_skills(self.project)
        self.assertEqual(report["skills"][0]["status"], "conflict")
        with self.assertRaises(WorkflowError):
            update_skills(self.project, apply=True)
        self.assertFalse((self.project / ".product-cycle").exists())

    def test_deleted_upstream_file_removed_only_when_local_tree_is_known(self):
        (self.source / "obsolete.md").write_text("Old reference")
        install_skills(self.project)
        (self.source / "obsolete.md").unlink()
        report = update_skills(self.project, apply=True)
        self.assertFalse((self.destination / self.source.name / "obsolete.md").exists())
        self.assertTrue((Path(report["backup"]) / self.source.name / "obsolete.md").is_file())

    def test_manifest_failure_rolls_back_replacement(self):
        install_skills(self.project)
        manifest = self.destination.parent / ".product-cycle-skills.json"
        previous = manifest.read_bytes()
        self.changed_bundle()
        with patch("product_cycle.installer.save_skill_manifest", side_effect=OSError("fixture failure")):
            with self.assertRaises(OSError):
                update_skills(self.project, apply=True)
        self.assertEqual((self.destination / self.source.name / "SKILL.md").read_text(), "Original instructions")
        self.assertFalse((self.destination / self.source.name / "reference.md").exists())
        self.assertEqual(manifest.read_bytes(), previous)

    def test_symlink_skill_is_rejected_without_touching_external_files(self):
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "SKILL.md").write_text("External instructions")
        self.destination.mkdir(parents=True)
        (self.destination / self.source.name).symlink_to(outside, target_is_directory=True)
        with self.assertRaises(WorkflowError):
            update_skills(self.project, apply=True)
        self.assertEqual((outside / "SKILL.md").read_text(), "External instructions")

    def test_cli_rejects_active_attempt_before_writing(self):
        with patch.dict("os.environ", {"PRODUCT_CYCLE_HOME": str(self.base / "state")}):
            store = Store.create(self.project, "Synthetic project", "Synthetic", mode="demo")
            store.begin("analysis", "work")
            store.close()
            with self.assertRaises(SystemExit), patch("builtins.print"):
                main(["update-skills", "--project", str(self.project), "--apply"])
        self.assertFalse((self.project / ".product-cycle/skill-backups").exists())

    def test_cli_records_updated_foundation_without_restarting_cycle(self):
        with patch.dict("os.environ", {"PRODUCT_CYCLE_HOME": str(self.base / "state")}):
            store = Store.create(self.project, "Synthetic project", "Synthetic")
            store.close()
            self.changed_bundle()
            with patch("builtins.print"):
                main(["update-skills", "--project", str(self.project), "--apply"])
            store = Store(self.project)
            try:
                self.assertEqual(store.foundation()["status"], "done")
                self.assertEqual(store.task("analysis")["revision"], 1)
                self.assertEqual(store.task("analysis")["status"], "pending")
                self.assertTrue(any(event["type"] == "skills.updated" for event in store.snapshot()["events"]))
            finally:
                store.close()

    def test_selection_leaves_other_customized_skill_untouched(self):
        second = self.base / "product-cycle-review"
        second.mkdir()
        (second / "SKILL.md").write_text("Review instructions")
        with patch("product_cycle.installer.skill_locations", return_value=(self.project, [self.source, second], self.destination)):
            install_skills(self.project)
            customized = self.destination / second.name / "SKILL.md"
            customized.write_text("Custom review")
            self.changed_bundle()
            report = update_skills(self.project, apply=True, selected=[self.source.name])
            self.assertEqual(customized.read_text(), "Custom review")
            self.assertEqual([row["name"] for row in report["skills"]], [self.source.name])

    def test_uninstall_preview_is_read_only(self):
        install_skills(self.project)
        manifest = self.destination.parent / ".product-cycle-skills.json"
        before = manifest.read_bytes()
        report = uninstall_skills(self.project)
        self.assertFalse(report["applied"])
        self.assertEqual(report["skills"], [{"name": self.source.name, "status": "remove"}])
        self.assertTrue((self.destination / self.source.name).is_dir())
        self.assertEqual(manifest.read_bytes(), before)
        self.assertFalse((self.project / ".product-cycle").exists())

    def test_force_uninstall_backs_up_customizations_and_preserves_other_skills(self):
        install_skills(self.project)
        target = self.destination / self.source.name
        (target / "SKILL.md").write_text("Custom instructions")
        (target / "notes.md").write_text("Keep these notes")
        other = self.destination / "unrelated-skill"
        other.mkdir()
        (other / "SKILL.md").write_text("Other instructions")
        with self.assertRaises(WorkflowError):
            uninstall_skills(self.project, apply=True)
        self.assertTrue(target.is_dir())
        report = uninstall_skills(self.project, apply=True, force=True)
        backup = Path(report["backup"]) / self.source.name
        self.assertEqual((backup / "SKILL.md").read_text(), "Custom instructions")
        self.assertEqual((backup / "notes.md").read_text(), "Keep these notes")
        self.assertFalse(target.exists())
        self.assertEqual((other / "SKILL.md").read_text(), "Other instructions")

    def test_uninstall_is_idempotent_and_allows_fresh_install(self):
        install_skills(self.project)
        report = uninstall_skills(self.project, apply=True)
        self.assertEqual((Path(report["backup"]) / self.source.name / "SKILL.md").read_text(), "Original instructions")
        self.assertEqual(uninstall_skills(self.project, apply=True)["skills"], [])
        self.assertIsNone(uninstall_skills(self.project, apply=True)["backup"])
        self.changed_bundle()
        install_skills(self.project)
        self.assertEqual((self.destination / self.source.name / "SKILL.md").read_text(), "Updated instructions")
        self.assertEqual(update_skills(self.project)["skills"][0]["status"], "unchanged")

    def test_uninstall_manifest_failure_restores_removed_skills(self):
        install_skills(self.project)
        manifest = self.destination.parent / ".product-cycle-skills.json"
        before = manifest.read_bytes()
        with patch("product_cycle.installer.save_skill_manifest", side_effect=OSError("fixture failure")):
            with self.assertRaises(OSError):
                uninstall_skills(self.project, apply=True)
        self.assertEqual((self.destination / self.source.name / "SKILL.md").read_text(), "Original instructions")
        self.assertEqual(manifest.read_bytes(), before)

    def test_force_uninstall_rejects_symlinks(self):
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "SKILL.md").write_text("External instructions")
        self.destination.mkdir(parents=True)
        (self.destination / self.source.name).symlink_to(outside, target_is_directory=True)
        with self.assertRaises(WorkflowError):
            uninstall_skills(self.project, apply=True, force=True)
        self.assertEqual((outside / "SKILL.md").read_text(), "External instructions")

    def test_cli_uninstall_and_reinstall_reject_active_attempt(self):
        with patch.dict("os.environ", {"PRODUCT_CYCLE_HOME": str(self.base / "state")}):
            store = Store.create(self.project, "Synthetic project", "Synthetic", mode="demo")
            install_skills(self.project)
            store.begin("analysis", "work")
            store.close()
            for command in [["uninstall-skills", "--apply", "--force"], ["install-skills"]]:
                with self.subTest(command=command), self.assertRaises(SystemExit), patch("builtins.print"):
                    main([*command, "--project", str(self.project)])
            self.assertTrue((self.destination / self.source.name).is_dir())
            self.assertFalse((self.project / ".product-cycle/skill-backups").exists())

    def test_cli_reinstall_preserves_cycle_and_records_new_foundation(self):
        with patch.dict("os.environ", {"PRODUCT_CYCLE_HOME": str(self.base / "state")}):
            store = Store.create(self.project, "Synthetic project", "Synthetic")
            store.owner_input("analysis", "Owner", "Keep the supplied direction")
            config = store.config
            brief = (store.root / "brief.md").read_bytes()
            store.close()
            with patch("builtins.print"):
                main(["uninstall-skills", "--project", str(self.project), "--apply"])
            store = Store(self.project)
            self.assertEqual(store.foundation()["status"], "blocked")
            store.close()
            self.changed_bundle()
            with patch("builtins.print"):
                main(["install-skills", "--project", str(self.project)])
            store = Store(self.project)
            try:
                self.assertEqual(store.foundation()["status"], "done")
                self.assertEqual(store.task("analysis")["revision"], 1)
                self.assertEqual(store.task("analysis")["status"], "pending")
                self.assertEqual(store.owner_inputs("analysis")[0]["note"], "Keep the supplied direction")
                self.assertEqual(store.config, config)
                self.assertEqual((store.root / "brief.md").read_bytes(), brief)
                self.assertTrue(any(event["type"] == "skills.uninstalled" for event in store.snapshot()["events"]))
                self.assertTrue(any(event["type"] == "skills.installed" for event in store.snapshot()["events"]))
            finally:
                store.close()

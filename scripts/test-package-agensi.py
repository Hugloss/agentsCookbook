#!/usr/bin/env python3
"""Exercise the immutable source and complete-artifact packaging contracts."""

import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("package_agensi", Path(__file__).with_name("package-agensi.py"))
packaging = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(packaging)


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "source"
        self.root.mkdir()
        self.output = self.root.parent / "output"
        self.git("init", "-q")
        self.manifest = {"packs": [
            {"id": "first", "name": "First pack", "summary": "First methodology.",
             "catalog_sections": ["First"]},
            {"id": "second", "name": "Second pack", "summary": "Second methodology.",
             "catalog_sections": ["Second"]},
        ]}
        self.write("distribution/agensi-packs.json", json.dumps(self.manifest))
        self.write("skills/README.md", "# Skills\n\n## First\n- `alpha` — First.\n"
                   "## Second\n- `beta` — Second.\n## Overlap boundaries\n- `not-a-skill`\n")
        self.write("LICENSE", "MIT License\nCopyright fixture\n")
        self.write("skills/alpha/SKILL.md", "---\nname: alpha\ndescription: First skill\n---\n"
                   "Read [reference](references/patterns.md).\n")
        self.write("skills/alpha/references/patterns.md", "# Patterns\nCanonical café.\n")
        self.write("skills/alpha/agents/openai.yaml", 'interface:\n  display_name: "Alpha"\n')
        self.write("skills/beta/SKILL.md", "---\nname: beta\ndescription: Second skill\n---\n# Beta\n")
        self.write("agents/native.md", "Native permissions must not travel in the skill pack.\n")
        self.write("adapters/pi/index.js", "// Native adapter must not be exported.\n")
        self.commit = self.save()
        self.first_pack = packaging.select_packs(self.source())[0][0]

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()

    def write(self, path, data):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data.encode() if isinstance(data, str) else data)

    def save(self):
        self.git("add", "-A")
        self.git("-c", "user.name=Packaging Test", "-c", "user.email=packaging@example.invalid",
                 "commit", "-qm", "Fixture")
        return self.git("rev-parse", "HEAD")

    def source(self):
        return packaging.read_revision(self.root, "HEAD")[1]

    def snapshot(self, directory):
        packs = {}
        for result in packaging.export(self.root, "HEAD", self.root.parent / directory):
            with zipfile.ZipFile(result["file"]) as archive:
                receipt = json.loads(archive.read("SOURCE.json"))
                packs[receipt["pack_id"]] = {"result": result, "receipt": receipt,
                                            "files": {name: archive.read(name) for name in archive.namelist()}}
        return packs

    def catalog(self, old, new):
        path = self.root / "skills/README.md"
        path.write_text(path.read_text().replace(old, new))

    def remove_skill(self, name):
        shutil.rmtree(self.root / "skills" / name)
        path = self.root / "skills/README.md"
        path.write_text("\n".join(line for line in path.read_text().splitlines()
                                  if not line.startswith(f"- `{name}`")) + "\n")

    def assert_rejected(self, pattern):
        self.save()
        with self.assertRaisesRegex(ValueError, pattern):
            packaging.export(self.root, "HEAD", self.output)
        self.assertFalse(self.output.exists(), "validation must finish before any artifacts are written")

    def test_complete_unchanged_archives_and_verifiable_provenance(self):
        results = packaging.export(self.root, "HEAD", self.output)
        self.assertEqual(len(results), 2)
        source = self.source()
        observed_skills = []
        for result in results:
            data = Path(result["file"]).read_bytes()
            self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(result["source_commit"], self.commit)
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = archive.namelist()
                self.assertEqual(names, sorted(names))
                receipt = json.loads(archive.read("SOURCE.json"))
                self.assertEqual(receipt["source_commit"], self.commit)
                self.assertEqual(receipt["manifest_sha256"], hashlib.sha256(source[packaging.MANIFEST]).hexdigest())
                self.assertEqual(set(receipt["files"]), set(names) - {"SOURCE.json"})
                digest = hashlib.sha256(json.dumps(receipt["files"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                self.assertEqual(receipt["content_sha256"], digest)
                self.assertEqual(result["content_sha256"], digest)
                self.assertEqual(archive.read("LICENSE"), source["LICENSE"])
                for name, digest in receipt["files"].items():
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), digest)
                observed_skills.extend(receipt["skills"])
                for name in names:
                    self.assertFalse(name.startswith(("agents/", "adapters/", "scripts/")))
                    if name.startswith("skills/"):
                        self.assertEqual(archive.read(name), source[name])
                for info in archive.infolist():
                    self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
        self.assertEqual(sorted(observed_skills), ["alpha", "beta"])
        with zipfile.ZipFile(self.output / "agents-cookbook-first.zip") as archive:
            self.assertIn("skills/alpha/references/patterns.md", archive.namelist())
            self.assertIn("skills/alpha/agents/openai.yaml", archive.namelist())
            readme = archive.read("README.md").decode()
            self.assertIn("### First\n", readme)
            self.assertIn("- [alpha](skills/alpha/SKILL.md) — First.", readme)
            self.assertNotIn("### Second\n", readme)
            self.assertIn("Start with one skill that matches the task.", readme)

    def test_dirty_worktree_and_export_attributes_cannot_change_committed_bytes(self):
        self.write(".gitattributes", "skills/alpha/references/patterns.md export-ignore\n"
                   "skills/beta/SKILL.md export-subst\n")
        self.write("skills/beta/SKILL.md", "$Format:%H$\n")
        self.save()
        first = packaging.export(self.root, "HEAD", self.output)
        original = {item["file"]: Path(item["file"]).read_bytes() for item in first}
        self.write("skills/alpha/SKILL.md", "Dirty instruction change\n")
        self.write("skills/alpha/untracked.md", "Not committed\n")
        self.write("skills/README.md", "Dirty invalid catalog\n")
        self.write("distribution/agensi-packs.json", "Dirty invalid manifest\n")
        second = packaging.export(self.root, "HEAD", self.output)
        self.assertEqual(first, second)
        for name, data in original.items():
            self.assertEqual(Path(name).read_bytes(), data)
        with zipfile.ZipFile(self.output / "agents-cookbook-first.zip") as archive:
            self.assertIn("skills/alpha/references/patterns.md", archive.namelist())
            self.assertNotIn("skills/alpha/untracked.md", archive.namelist())
        with zipfile.ZipFile(self.output / "agents-cookbook-second.zip") as archive:
            self.assertEqual(archive.read("skills/beta/SKILL.md"), b"$Format:%H$\n")

    def test_explicit_old_revision_remains_reproducible_after_new_commit(self):
        first = packaging.export(self.root, self.commit, self.output)
        self.write("skills/beta/SKILL.md", "Changed methodology\n")
        self.save()
        self.assertEqual(packaging.export(self.root, self.commit, self.output), first)
        with self.assertRaisesRegex(ValueError, "fresh directory"):
            packaging.export(self.root, "HEAD", self.output)
        changed = packaging.export(self.root, "HEAD", self.root.parent / "new-output")
        self.assertNotEqual([item["sha256"] for item in changed], [item["sha256"] for item in first])

    def test_commit_only_and_other_pack_metadata_do_not_change_content_identity(self):
        before = self.snapshot("before")
        self.write("docs/unrelated.md", "Unrelated repository documentation.\n")
        self.save()
        after = self.snapshot("after")
        for identity in before:
            self.assertEqual(before[identity]["result"]["content_sha256"], after[identity]["result"]["content_sha256"])
            self.assertNotEqual(before[identity]["result"]["sha256"], after[identity]["result"]["sha256"])
            self.assertNotEqual(before[identity]["receipt"]["source_commit"], after[identity]["receipt"]["source_commit"])
        self.manifest["packs"][0]["summary"] = "Updated listing description."
        self.write(packaging.MANIFEST, json.dumps(self.manifest))
        self.save()
        metadata = self.snapshot("metadata")
        self.assertNotEqual(after["first"]["result"]["content_sha256"], metadata["first"]["result"]["content_sha256"])
        self.assertEqual(after["second"]["result"]["content_sha256"], metadata["second"]["result"]["content_sha256"])
        self.assertNotEqual(after["second"]["receipt"]["manifest_sha256"], metadata["second"]["receipt"]["manifest_sha256"])
        self.catalog("- `alpha` — First.", "- `alpha` — Focused alpha inspection.")
        self.save()
        described = self.snapshot("catalog-description")
        self.assertNotEqual(metadata["first"]["result"]["content_sha256"], described["first"]["result"]["content_sha256"])
        self.assertEqual(metadata["second"]["result"]["content_sha256"], described["second"]["result"]["content_sha256"])
        self.assertEqual(metadata["first"]["files"]["skills/alpha/SKILL.md"], described["first"]["files"]["skills/alpha/SKILL.md"])
        self.assertIn(b"Focused alpha inspection.", described["first"]["files"]["README.md"])

    def test_skill_and_resource_updates_change_only_owning_pack_content(self):
        before = self.snapshot("before")
        self.write("skills/alpha/SKILL.md", "# Changed review\nRead [reference](references/patterns.md).\n")
        self.write("skills/alpha/references/patterns.md", "Updated canonical reference.\n")
        self.write("skills/alpha/references/extra.md", "Additional reference.\n")
        self.save()
        updated = self.snapshot("updated")
        self.assertNotEqual(before["first"]["result"]["content_sha256"], updated["first"]["result"]["content_sha256"])
        self.assertEqual(before["second"]["result"]["content_sha256"], updated["second"]["result"]["content_sha256"])
        self.assertEqual(updated["first"]["files"]["skills/alpha/references/patterns.md"], b"Updated canonical reference.\n")
        (self.root / "skills/alpha/references/extra.md").unlink()
        self.save()
        removed = self.snapshot("removed-resource")
        self.assertNotIn("skills/alpha/references/extra.md", removed["first"]["files"])
        self.assertNotEqual(updated["first"]["result"]["content_sha256"], removed["first"]["result"]["content_sha256"])

    def test_skill_addition_and_deletion_need_no_manifest_changes(self):
        before = self.snapshot("before")
        manifest = (self.root / packaging.MANIFEST).read_bytes()
        self.write("skills/gamma/SKILL.md", "# Gamma\n")
        self.catalog("## First\n", "## First\n- `gamma` — New.\n")
        self.save()
        added = self.snapshot("added")
        self.assertEqual(added["first"]["receipt"]["skills"], ["alpha", "gamma"])
        self.assertNotEqual(before["first"]["result"]["content_sha256"], added["first"]["result"]["content_sha256"])
        self.assertEqual(before["second"]["result"]["content_sha256"], added["second"]["result"]["content_sha256"])
        self.remove_skill("alpha")
        self.save()
        deleted = self.snapshot("deleted")
        self.assertEqual(deleted["first"]["receipt"]["skills"], ["gamma"])
        self.assertFalse(any(path.startswith("skills/alpha/") for path in deleted["first"]["files"]))
        self.assertNotEqual(added["first"]["result"]["content_sha256"], deleted["first"]["result"]["content_sha256"])
        self.assertEqual(manifest, (self.root / packaging.MANIFEST).read_bytes())

    def test_rename_keeps_complete_resources_and_removes_old_paths(self):
        before = self.snapshot("before")
        (self.root / "skills/alpha").rename(self.root / "skills/omega")
        skill = self.root / "skills/omega/SKILL.md"
        skill.write_text(skill.read_text().replace("name: alpha", "name: omega"))
        self.catalog("- `alpha`", "- `omega`")
        self.save()
        renamed = self.snapshot("renamed")
        self.assertEqual(renamed["first"]["receipt"]["skills"], ["omega"])
        self.assertIn("skills/omega/references/patterns.md", renamed["first"]["files"])
        self.assertIn("skills/omega/agents/openai.yaml", renamed["first"]["files"])
        self.assertFalse(any(path.startswith("skills/alpha/") for path in renamed["first"]["files"]))
        self.assertNotEqual(before["first"]["result"]["content_sha256"], renamed["first"]["result"]["content_sha256"])
        self.assertEqual(before["second"]["result"]["content_sha256"], renamed["second"]["result"]["content_sha256"])

    def test_moving_a_skill_updates_both_pack_memberships(self):
        self.write("skills/gamma/SKILL.md", "# Gamma\n")
        self.catalog("## First\n", "## First\n- `gamma` — Retained.\n")
        self.save()
        before = self.snapshot("before")
        self.catalog("- `alpha` — First.\n", "")
        self.catalog("## Second\n", "## Second\n- `alpha` — Moved.\n")
        self.save()
        moved = self.snapshot("moved")
        self.assertEqual(moved["first"]["receipt"]["skills"], ["gamma"])
        self.assertEqual(moved["second"]["receipt"]["skills"], ["alpha", "beta"])
        self.assertFalse(any(path.startswith("skills/alpha/") for path in moved["first"]["files"]))
        self.assertIn("skills/alpha/references/patterns.md", moved["second"]["files"])
        for identity in before:
            self.assertNotEqual(before[identity]["result"]["content_sha256"], moved[identity]["result"]["content_sha256"])

    def test_empty_known_category_is_allowed_but_empty_pack_requires_action(self):
        self.write("skills/gamma/SKILL.md", "# Gamma\n")
        self.catalog("## Second\n", "## Extra\n- `gamma` — Retained.\n## Second\n")
        self.manifest["packs"][0]["catalog_sections"].append("Extra")
        self.write(packaging.MANIFEST, json.dumps(self.manifest))
        self.remove_skill("alpha")
        self.save()
        remaining = self.snapshot("remaining")
        self.assertEqual(remaining["first"]["receipt"]["skills"], ["gamma"])
        self.assertNotIn(b"### First\n", remaining["first"]["files"]["README.md"])
        self.assertIn(b"### Extra\n", remaining["first"]["files"]["README.md"])
        self.remove_skill("gamma")
        self.assert_rejected("pack first has no skills; remove its manifest entry")
        self.manifest["packs"].pop(0)
        self.write(packaging.MANIFEST, json.dumps(self.manifest))
        self.save()
        removed = self.snapshot("removed-pack")
        self.assertEqual(set(removed), {"second"})
        self.assertEqual(removed["second"]["result"]["content_sha256"], remaining["second"]["result"]["content_sha256"])

    def test_new_category_requires_explicit_pack_assignment(self):
        self.write("skills/gamma/SKILL.md", "# Gamma\n")
        self.catalog("## Overlap boundaries\n", "## New category\n- `gamma` — New.\n## Overlap boundaries\n")
        self.assert_rejected("manifest omits catalog sections.*New category")
        self.manifest["packs"][0]["catalog_sections"].append("New category")
        self.write(packaging.MANIFEST, json.dumps(self.manifest))
        self.save()
        assigned = self.snapshot("assigned")
        self.assertEqual(assigned["first"]["receipt"]["skills"], ["alpha", "gamma"])

    def test_existing_unrelated_output_is_preserved_and_rejected(self):
        self.output.mkdir()
        unrelated = self.output / "other.txt"
        unrelated.write_text("Keep this\n")
        with self.assertRaisesRegex(ValueError, "fresh directory"):
            packaging.export(self.root, "HEAD", self.output)
        self.assertEqual(list(self.output.iterdir()), [unrelated])
        self.assertEqual(unrelated.read_text(), "Keep this\n")

    def test_listing_metadata_limits_and_unique_names(self):
        for field, content in [("name", "x" * 61), ("summary", "x" * 301), ("name", "Second pack")]:
            with self.subTest(field=field, value=content):
                source = self.source()
                manifest = json.loads(json.dumps(self.manifest))
                manifest["packs"][0][field] = content
                source[packaging.MANIFEST] = json.dumps(manifest).encode()
                with self.assertRaisesRegex(ValueError, "unique name"):
                    packaging.select_packs(source)

    def test_unknown_repeated_and_omitted_sections_fail(self):
        variants = [(["Missing"], ["Second"]), (["First"], ["First", "Second"]),
                    (["First"], ["First"])]
        for first, second in variants:
            with self.subTest(first=first, second=second):
                manifest = json.loads(json.dumps(self.manifest))
                manifest["packs"][0]["catalog_sections"] = first
                manifest["packs"][1]["catalog_sections"] = second
                source = self.source()
                source[packaging.MANIFEST] = json.dumps(manifest).encode()
                with self.assertRaises(ValueError):
                    packaging.select_packs(source)
        self.manifest["packs"].pop()
        self.write(packaging.MANIFEST, json.dumps(self.manifest))
        self.assert_rejected("omits catalog sections")

    def test_missing_unknown_and_repeated_catalog_members_fail(self):
        variants = ["- `alpha`\n", "- `alpha`\n- `ghost`\n- `beta`\n",
                    "- `alpha`\n- `alpha`\n- `beta`\n"]
        for members in variants:
            with self.subTest(members=members):
                source = self.source()
                source["skills/README.md"] = ("## First\n" + members).encode()
                with self.assertRaises(ValueError):
                    packaging.select_packs(source)

    def test_missing_reference_fails_before_output(self):
        self.write("skills/beta/SKILL.md", "[missing][target]\n\n[target]: references/missing.md\n")
        self.assert_rejected("missing local reference")

    def test_symlink_binary_and_unsafe_path_are_not_packaged(self):
        source = self.source()
        for path, content in [("skills/alpha/link.md", None),
                              ("skills/alpha/binary.dat", b"\xff"),
                              ("skills/alpha/control.dat", b"\x00"),
                              ("skills/alpha/unsafe\\file.md", b"text")]:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    packaging.make_bundle(source | {path: content}, self.commit,
                                          self.first_pack, ["alpha"])
        (self.root / "skills/alpha/link.md").symlink_to("references/patterns.md")
        self.assert_rejected("non-regular file")

    def test_local_reference_cannot_escape_export(self):
        source = self.source()
        for link in ["../../../outside.md", "/absolute.md", "references/%2e%2e/%2e%2e/%2e%2e/outside.md"]:
            with self.subTest(link=link):
                changed = source | {"skills/alpha/SKILL.md": f"[escape]({link})\n".encode()}
                with self.assertRaises(ValueError):
                    packaging.make_bundle(changed, self.commit, self.first_pack, ["alpha"])

    def test_real_skill_count_limit_and_unexpected_nested_skills(self):
        source = self.source()
        source["skills/README.md"] = ("## First\n" + "".join(f"- `skill-{i}`\n" for i in range(50))).encode()
        source[packaging.MANIFEST] = json.dumps({"packs": [self.manifest["packs"][0]]}).encode()
        source = {path: data for path, data in source.items() if not path.startswith(("skills/alpha/", "skills/beta/"))}
        for number in range(50):
            source[f"skills/skill-{number}/SKILL.md"] = b"# Skill\n"
        pack, names = packaging.select_packs(source)[0]
        data, _ = packaging.make_bundle(source, self.commit, pack, names)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertEqual(sum(path.endswith("/SKILL.md") for path in archive.namelist()), 50)
        source["skills/README.md"] += b"- `skill-50`\n"
        source["skills/skill-50/SKILL.md"] = b"# Skill\n"
        with self.assertRaisesRegex(ValueError, "1.*50 skills"):
            packaging.select_packs(source)
        source = self.source() | {"skills/alpha/nested/SKILL.md": b"Unexpected skill\n"}
        with self.assertRaisesRegex(ValueError, "unexpected SKILL.md"):
            packaging.make_bundle(source, self.commit, self.first_pack, ["alpha"])

    def test_file_text_and_zip_delivery_limits(self):
        source = self.source()
        for number in range(201):
            source[f"skills/alpha/references/extra-{number}.md"] = b"Extra\n"
        with self.assertRaisesRegex(ValueError, "supporting-text delivery limits"):
            packaging.make_bundle(source, self.commit, self.first_pack, ["alpha"])
        for constant, message in [("MAX_TEXT_CHARS", "text delivery limit"), ("MAX_ZIP_BYTES", "ZIP upload limit")]:
            with self.subTest(limit=constant), patch.object(packaging, constant, 1):
                with self.assertRaisesRegex(ValueError, message):
                    packaging.make_bundle(self.source(), self.commit, self.first_pack, ["alpha"])


if __name__ == "__main__":
    unittest.main()

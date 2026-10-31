#!/usr/bin/env python3
"""Build portable Agensi website-upload ZIPs from one immutable Git revision."""

import argparse
import hashlib
import io
import json
import posixpath
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit


REPOSITORY = "https://github.com/Hugloss/agentsCookbook"
MANIFEST = "distribution/agensi-packs.json"
MAX_SKILLS = 50
MAX_FILES = 1000
MAX_OTHER_TEXT_FILES = 200
MAX_TEXT_CHARS = 6_000_000
MAX_ZIP_BYTES = 50_000_000


def fail(message):
    raise ValueError(message)


def safe_path(path):
    if (not path or path.startswith("/") or "\\" in path or ":" in path
            or any(part in ("", ".", "..") for part in path.split("/"))):
        fail(f"unsafe package path: {path!r}")


def text_file(files, path):
    safe_path(path)
    data = files.get(path)
    if data is None:
        fail(f"missing or non-regular file (including symlink): {path}")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        fail(f"file is not UTF-8 text: {path}")
    if any(ord(char) < 32 and char not in "\t\r\n" for char in text):
        fail(f"file contains non-text control characters: {path}")
    return text


def read_revision(root, ref):
    def git(*args, input_data=None):
        return subprocess.run(["git", "-C", str(root), *args], check=True,
                              input=input_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

    commit = git("rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}").decode().strip()
    entries, files = [], {}
    for entry in git("ls-tree", "-r", "-z", "--full-tree", commit).split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        path = path.decode("utf-8")
        files[path] = None
        if kind == b"blob" and mode in (b"100644", b"100755"):
            entries.append((path, oid))
    # Read blobs directly: export-ignore/export-subst attributes must not omit or alter source bytes.
    stream = io.BytesIO(git("cat-file", "--batch", input_data=b"".join(oid + b"\n" for _, oid in entries)))
    for path, _ in entries:
        _, _, size = stream.readline().split()
        files[path] = stream.read(int(size))
        stream.read(1)
    return commit, files


def select_packs(files):
    canonical = {path.split("/")[1] for path in files
                 if re.fullmatch(r"skills/[^/]+/SKILL\.md", path)}
    sections, descriptions, members, current = {}, {}, set(), None
    for line in text_file(files, "skills/README.md").splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            if current == "Overlap boundaries":
                break
            if current in sections:
                fail(f"duplicate catalog section: {current}")
            sections[current] = []
        match = re.match(r"^- `([^`]+)`", line)
        if match and current:
            name = match.group(1)
            if name not in canonical or name in members:
                fail(f"unknown or repeated catalog skill: {name}")
            sections[current].append(name)
            descriptions[name] = line[match.end():]
            members.add(name)
    if members != canonical or not canonical:
        fail(f"catalog does not cover canonical skills: {sorted(canonical - members)}")
    manifest = json.loads(text_file(files, MANIFEST))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("packs"), list):
        fail("manifest must contain a packs list")
    result, used_sections, used_ids, used_names = [], set(), set(), set()
    for pack in manifest["packs"]:
        if not isinstance(pack, dict):
            fail("each pack must be an object")
        identity = pack.get("id")
        if (not isinstance(identity, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identity)
                or identity in used_ids):
            fail(f"invalid or duplicate pack id: {identity!r}")
        if any(not isinstance(pack.get(key), str) or not pack[key].strip()
               for key in ("name", "summary")):
            fail(f"pack {identity} needs a name and summary")
        if (len(pack["name"].encode("utf-16-le")) // 2 > 60
                or len(pack["summary"].encode("utf-16-le")) // 2 > 300
                or pack["name"].casefold() in used_names):
            fail(f"pack {identity} needs a unique name of at most 60 characters and summary of at most 300")
        selected = pack.get("catalog_sections")
        if not isinstance(selected, list) or not selected:
            fail(f"pack {identity} needs catalog_sections")
        names = []
        for section in selected:
            if not isinstance(section, str) or section not in sections or section in used_sections:
                fail(f"unknown or repeated catalog section: {section!r}")
            names.extend(sections[section])
            used_sections.add(section)
        if not names:
            fail(f"pack {identity} has no skills; remove its manifest entry or assign a nonempty catalog section")
        if len(names) > MAX_SKILLS:
            fail(f"pack {identity} must contain 1–{MAX_SKILLS} skills; found {len(names)}")
        navigation = {section: [(name, descriptions[name]) for name in sections[section]]
                      for section in selected if sections[section]}
        result.append((dict(pack, catalog_entries=navigation), sorted(names)))
        used_ids.add(identity)
        used_names.add(pack["name"].casefold())
    missing = {section for section, names in sections.items() if names} - used_sections
    if missing:
        fail(f"manifest omits catalog sections: {sorted(missing)}")
    return result


def check_local_links(files):
    for path in files:
        if not path.lower().endswith(".md"):
            continue
        text = text_file(files, path)
        links = re.findall(r"\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)", text)
        links += re.findall(r"^\[[^\]\n]+\]:\s*(<[^>]+>|\S+)", text, re.MULTILINE)
        for link in links:
            url = urlsplit(link.strip("<>"))
            if url.scheme or url.netloc or not url.path:
                continue
            target = unquote(url.path)
            if target.startswith("/") or "\\" in target:
                fail(f"unsafe local reference in {path}: {link}")
            target = posixpath.normpath(posixpath.join(str(PurePosixPath(path).parent), target))
            safe_path(target)
            if target not in files:
                fail(f"missing local reference in {path}: {link}")


def make_bundle(source, commit, pack, names):
    roots = tuple(f"skills/{name}/" for name in names)
    files = {path: data for path, data in source.items() if path.startswith(roots)}
    files["LICENSE"] = source.get("LICENSE")
    navigation = "".join(f"### {section}\n\n" + "".join(
        f"- [{name}](skills/{name}/SKILL.md){description}\n" for name, description in entries)
        + "\n" for section, entries in pack["catalog_entries"].items())
    readme = (f"# {pack['name']}\n\n{pack['summary']}\n\n"
              f"Source repository: {REPOSITORY}\n\n"
              "The exact source revision is recorded as `source_commit` in [SOURCE.json](SOURCE.json).\n\n"
              "These are portable skill instructions. Your host owns execution, tools, "
              "permissions, models, and sessions. Packaging does not qualify runtime behavior.\n\n"
              "On Agensi, retrieve referenced files through its connector using the listing slug "
              "and archive path; local installation is not assumed. In a native host, resolve "
              "references relative to the complete installed skill folder.\n\n"
              "Start with one skill that matches the task. Load its instructions and required "
              "references. Add another skill when the task or an explicit handoff calls for it.\n\n"
              "## Included skills\n\n"
              + navigation
              + "\nSOURCE.json hashes every other file in this ZIP; it excludes itself.\n")
    files["README.md"] = readme.encode("utf-8")
    for path in files:
        text_file(files, path)
    file_hashes = {path: hashlib.sha256(data).hexdigest() for path, data in sorted(files.items())}
    content_hash = hashlib.sha256(json.dumps(file_hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    receipt = {"schema_version": 1, "source_repository": REPOSITORY,
               "source_commit": commit, "pack_id": pack["id"], "skills": names,
               "manifest_sha256": hashlib.sha256(source[MANIFEST]).hexdigest(),
               "content_sha256": content_hash, "files": file_hashes}
    files["SOURCE.json"] = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    skill_count = sum(PurePosixPath(path).name == "SKILL.md" for path in files)
    if skill_count != len(names) or not 1 <= skill_count <= MAX_SKILLS:
        fail(f"pack {pack['id']} has unexpected SKILL.md files or exceeds the skill limit")
    if len(files) > MAX_FILES or len(files) - skill_count > MAX_OTHER_TEXT_FILES:
        fail(f"pack {pack['id']} exceeds file or supporting-text delivery limits")
    # UTF-16 code units are conservative for services counting JavaScript strings.
    chars = sum(len(text_file(files, path).encode("utf-16-le")) // 2 for path in files)
    if chars > MAX_TEXT_CHARS:
        fail(f"pack {pack['id']} exceeds the {MAX_TEXT_CHARS}-character text delivery limit")
    check_local_links(files)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for path, data in sorted(files.items()):
            entry = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    data = output.getvalue()
    if len(data) > MAX_ZIP_BYTES:
        fail(f"pack {pack['id']} exceeds the {MAX_ZIP_BYTES}-byte ZIP upload limit")
    return data, content_hash


def export(root, ref, output_dir):
    commit, source = read_revision(root, ref)
    bundles = {f"agents-cookbook-{pack['id']}.zip": make_bundle(source, commit, pack, names)
               for pack, names in select_packs(source)}
    if output_dir.exists():
        existing = list(output_dir.iterdir())
        if existing and (set(path.name for path in existing) != set(bundles)
                         or any(path.is_symlink() or not path.is_file()
                                or path.read_bytes() != bundles[path.name][0] for path in existing)):
            fail("output directory contains other artifacts; use a fresh directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for name, (data, content_hash) in bundles.items():
        target = output_dir / name
        with tempfile.NamedTemporaryFile(dir=output_dir, delete=False) as temporary:
            temporary.write(data)
            temporary_path = Path(temporary.name)
        try:
            temporary_path.replace(target)
        finally:
            temporary_path.unlink(missing_ok=True)
        results.append({"file": str(target), "sha256": hashlib.sha256(data).hexdigest(),
                        "content_sha256": content_hash, "bytes": len(data), "source_commit": commit})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD", help="committed source revision (default: HEAD)")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = Path(__file__).resolve().parent.parent
        print(json.dumps(export(root, args.ref, args.output_dir), indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Agensi packaging failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

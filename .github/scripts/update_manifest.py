#!/usr/bin/env python3
"""Add (or replace) a built plugin zip's version entry in a Jellyfin repo manifest.

Usage:
    update_manifest.py <zip_path> <asset_base_url> <manifest_path>

The zip is a JPRM-built plugin package containing meta.json at its root. We read
that meta.json as the source of truth, compute the zip's MD5 (what Jellyfin
validates against), and upsert the version entry into the manifest, keyed by the
plugin GUID. Existing plugin metadata (description/overview/imageUrl/...) is left
untouched — only the `versions` list is modified.
"""
import hashlib
import json
import os
import sys
import zipfile


def main():
    if len(sys.argv) != 4:
        sys.exit("usage: update_manifest.py <zip_path> <asset_base_url> <manifest_path>")
    zip_path, asset_base, manifest_path = sys.argv[1], sys.argv[2], sys.argv[3]
    asset_base = asset_base.rstrip("/") + "/"
    fname = os.path.basename(zip_path)

    with open(zip_path, "rb") as f:
        md5 = hashlib.md5(f.read()).hexdigest()
    meta = json.loads(zipfile.ZipFile(zip_path).read("meta.json"))

    entry = {
        "version": meta["version"],
        "changelog": meta.get("changelog", ""),
        "targetAbi": meta["targetAbi"],
        "sourceUrl": asset_base + fname,
        "checksum": md5,
        "timestamp": meta["timestamp"],
    }

    manifest = []
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)

    guid = meta["guid"]
    plugin = next((p for p in manifest if p.get("guid") == guid), None)
    if plugin is None:
        plugin = {
            "guid": guid,
            "name": meta["name"],
            "description": meta.get("description", ""),
            "overview": meta.get("overview", ""),
            "owner": meta.get("owner", ""),
            "category": meta.get("category", "General"),
            "versions": [],
        }
        manifest.append(plugin)

    versions = [v for v in plugin.get("versions", []) if v.get("version") != entry["version"]]
    versions.append(entry)
    versions.sort(key=lambda v: [int(x) for x in v["version"].split(".")], reverse=True)
    plugin["versions"] = versions

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=4)
        f.write("\n")

    print(f"manifest updated: {entry['version']} checksum={md5} sourceUrl={entry['sourceUrl']}")


if __name__ == "__main__":
    main()
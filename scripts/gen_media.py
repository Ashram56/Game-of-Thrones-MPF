#!/usr/bin/env python3
"""Copy the media the committed config references into the game's gitignored folders (never committed).

  python scripts/gen_media.py [--assets /mnt/project-files/got/assets] [--data DIR]

Sounds -> game/sounds/<track>/<file> (core set from rules.yaml `sounds`); DMD frames of rules.yaml `dmd.videos`
-> game/images/dmd_vidNNN_fKKK.png (128x32 as extracted; copied unchanged). Writes game/config/rom/dmd_frames.json
(video -> frame count, fps) for the slide player. Frames and sounds are copyrighted ROM media: gitignored.
"""
import argparse
import csv
import json
import os
import shutil
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default=os.environ.get("GOT_ASSETS", "/mnt/project-files/got/assets"))
    ap.add_argument("--data", default=os.environ.get("GOT_DATA", os.path.join(ROOT, "..", "Game-of-Thrones", "data")))
    a = ap.parse_args()
    sounds = yaml.safe_load(open(os.path.join(GAME, "config", "rom", "sounds.yaml"), encoding="utf-8"))["sounds"]
    missing = 0
    for name, s in sounds.items():
        src = os.path.join(a.assets, "audio", s["file"])
        dst_dir = os.path.join(GAME, "sounds", s["track"])
        os.makedirs(dst_dir, exist_ok=True)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(dst_dir, s["file"]))
        else:
            missing += 1
    rules = yaml.safe_load(open(os.path.join(GAME, "config", "rules.yaml"), encoding="utf-8"))
    vids = {int(r["video_id"]): r for r in csv.DictReader(open(os.path.join(a.data, "dmd_videos.csv"), encoding="utf-8"))}
    os.makedirs(os.path.join(GAME, "images"), exist_ok=True)
    manifest = {}
    for vid in sorted(set(rules["dmd"]["videos"].values())):
        v = vids[int(vid)]
        n = 0
        for k, img in enumerate(range(int(v["first_image"]), int(v["last_image"]) + 1)):
            src = os.path.join(a.assets, "dmd", "animations", "img%05d.png" % img)
            if not os.path.exists(src):
                src = os.path.join(a.assets, "dmd", "images", "pictures", "img%05d.png" % img)
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(GAME, "images", "dmd_vid%03d_f%03d.png" % (vid, k)))
                n += 1
        manifest["vid%03d" % vid] = {"frames": n, "fps": rules["dmd"]["fps"]}
    with open(os.path.join(GAME, "config", "rom", "dmd_frames.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print("sounds copied (missing %d), videos %s" % (missing, manifest))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())

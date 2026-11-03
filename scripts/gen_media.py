#!/usr/bin/env python3
"""Copy the media the committed config references into the game's gitignored folders (never committed).

  python scripts/gen_media.py [--assets /mnt/project-files/got/assets] [--data DIR]

Sounds -> game/sounds/<track>/<stem>.ogg (all sound effects, converted with ffmpeg); DMD frames of every video in data/dmd_videos.csv
-> game/images/dmd_vidNNN_fKKK.png (128x32 as extracted; copied unchanged). Writes game/config/rom/dmd_frames.json
(video -> frame count, fps) for the slide player. Frames and sounds are copyrighted ROM media: gitignored.
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default=os.environ.get("GOT_ASSETS", "/mnt/project-files/got/assets"))
    ap.add_argument("--data", default=os.environ.get("GOT_DATA", os.path.join(ROOT, "..", "Game-of-Thrones", "data")))
    a = ap.parse_args()
    sounds = json.load(open(os.path.join(GAME, "config", "rom", "sound_files.json"), encoding="utf-8"))
    ffmpeg = shutil.which("ffmpeg")

    def convert(item):
        name, s = item
        src = os.path.join(a.assets, "audio", s.get("src", s["file"]))
        dst_dir = os.path.join(GAME, "sounds", s["track"])
        dst = os.path.join(dst_dir, s["file"])
        os.makedirs(dst_dir, exist_ok=True)
        if not os.path.exists(src):
            return 1
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            return 0
        if s["file"].endswith(".ogg") and ffmpeg:               # WAV (860 MB) -> OGG Vorbis, about a tenth of the size
            r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", src, "-c:a", "libvorbis", "-q:a", "3", dst])
            return 1 if r.returncode else 0
        shutil.copyfile(src, dst)
        return 0

    with ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as ex:
        missing = sum(ex.map(convert, sorted(sounds.items())))
    rules = yaml.safe_load(open(os.path.join(GAME, "config", "rules.yaml"), encoding="utf-8"))
    vids = {int(r["video_id"]): r for r in csv.DictReader(open(os.path.join(a.data, "dmd_videos.csv"), encoding="utf-8"))}
    os.makedirs(os.path.join(GAME, "images"), exist_ok=True)
    manifest = {}
    for vid in sorted(set(rules["dmd"]["videos"].values()) | set(vids)):
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
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import dmd_text                                             # ROM text screens, drawn with the ROM bitmap fonts
    texts = dmd_text.rom_lines(a.data)
    fdir = os.path.join(GAME, "images", "fonts")
    os.makedirs(fdir, exist_ok=True)
    for n in range(32):                                         # glyph tables for the live (run-time value) text screens
        src = os.path.join(a.data, "fonts", "font%02d.json" % n)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(fdir, "font%02d.json" % n))
    for name, pages in texts.items():
        if dmd_text.is_live(pages):
            continue
        for i, page in enumerate(pages):
            dmd_text.render(a.data, page, os.path.join(GAME, "images", "tx", "tx_%s_p%d.png" % (name[4:], i)))
    print("text screens drawn: %d effects" % len(texts))
    print("sounds copied (missing %d), videos %s" % (missing, manifest))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())

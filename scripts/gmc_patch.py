#!/usr/bin/env python3
"""Patch the installed mpf-gmc 1.0.0 add-on (idempotent): keep the unfinished tail of a socket read.

MPF's big `settings` BCP message splits across reads; GMC parsed each read as whole lines and its BCP thread died
(no sound after that).   python scripts/gmc_patch.py [game/addons/mpf-gmc]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
addon = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "game", "addons", "mpf-gmc")
p = os.path.join(addon, "scripts", "bcp_server.gd")
s = open(p, encoding="utf-8").read()
if "_rx_tail" in s or "mpf-godot fix" in s or "tron patch" in s:
    print("already patched")
    sys.exit(0)
old = '\t\tvar messages := _client.get_string(bytes).split("\\n")\n'
new = ('\t\tvar _rx_text: String = _rx_tail + _client.get_string(bytes)\n'
       '\t\tvar messages := _rx_text.split("\\n")\n'
       '\t\t_rx_tail = messages[messages.size() - 1]\n'
       '\t\tmessages.resize(messages.size() - 1)\n')
assert old in s, "bcp_server.gd differs from GMC 1.0.0"
s = s.replace(old, new)
i = s.index("\nfunc ")
s = s[:i] + "\nvar _rx_tail := \"\"\n" + s[i:]
open(p, "w", encoding="utf-8").write(s)
print("patched", p)

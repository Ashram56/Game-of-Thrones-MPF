"""Fallback when pytest is not installed: runs the test_* functions of tests/test_structure.py (skips handled)."""
import os, sys, types, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
class _M(types.ModuleType):
    class mark:
        @staticmethod
        def skipif(cond, reason=""):
            def d(f):
                f._skip = cond
                return f
            return d
sys.modules.setdefault("pytest", _M("pytest"))
from tests import test_structure as t
bad = 0
for n, f in sorted(vars(t).items()):
    if n.startswith("test_") and callable(f):
        if getattr(f, "_skip", False):
            print("SKIP", n); continue
        try:
            f(); print("ok  ", n)
        except Exception:
            bad += 1; print("FAIL", n); traceback.print_exc()
sys.exit(1 if bad else 0)

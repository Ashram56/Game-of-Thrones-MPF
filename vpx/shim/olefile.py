"""Minimal pure-Python stand-in for olefile (OleFileIO, listdir, openstream, exists) for vpx_extract.py.

Only for machines where `pip install olefile` is impossible. Reads OLE2 compound files (v3/v4) fully into memory.
Use: PYTHONPATH=vpx/shim python3 tools/vpx/vpx_extract.py ...
"""
import io
import struct

MAGIC = bytes.fromhex("d0cf11e0a1b11ae1")
FREE, ENDCHAIN = 0xFFFFFFFF, 0xFFFFFFFE


class OleFileIO:
    def __init__(self, path):
        with open(path, "rb") as f:
            self.d = f.read()
        d = self.d
        if d[:8] != bytes.fromhex("d0cf11e0a1b11ae1"):
            raise OSError("not an OLE2 file")
        shift, mshift = struct.unpack_from("<HH", d, 30)
        self.ss, self.mss = 1 << shift, 1 << mshift
        nfat, dirstart, _, cutoff, mfstart, nmf, difstart, ndif = struct.unpack_from("<IIIIIIII", d, 44)
        self.cutoff = cutoff
        difat = list(struct.unpack_from("<109I", d, 76))
        sec = difstart
        for _ in range(ndif):
            vals = struct.unpack_from("<%dI" % (self.ss // 4), self._sec(sec))
            difat += vals[:-1]
            sec = vals[-1]
        fat = []
        for s in difat[:nfat]:
            fat += struct.unpack_from("<%dI" % (self.ss // 4), self._sec(s))
        self.fat = fat
        self.minifat = []
        if nmf:
            mf = self._chain(mfstart, self.fat)
            self.minifat = list(struct.unpack("<%dI" % (len(mf) // 4), mf))
        dirdata = self._chain(dirstart, self.fat)
        self.entries = []
        for i in range(len(dirdata) // 128):
            e = dirdata[i * 128:(i + 1) * 128]
            nl = struct.unpack_from("<H", e, 64)[0]
            name = e[:max(0, nl - 2)].decode("utf-16-le")
            typ = e[66]
            left, right, child = struct.unpack_from("<III", e, 68)
            start = struct.unpack_from("<I", e, 116)[0]
            size = struct.unpack_from("<Q", e, 120)[0] & 0xFFFFFFFF
            self.entries.append((name, typ, left, right, child, start, size))
        self.ministream = self._chain(self.entries[0][5], self.fat) if self.entries else b""
        self.paths = {}
        self._walk(self.entries[0][4], [])

    def _sec(self, n):
        o = (n + 1) * self.ss
        return self.d[o:o + self.ss]

    def _chain(self, start, fat):
        out, seen = [], set()
        while start < 0xFFFFFFFA and start not in seen:
            seen.add(start)
            out.append(self._sec(start))
            start = fat[start]
        return b"".join(out)

    def _walk(self, idx, prefix):
        stack, order = [idx], []
        # in-order traversal of the red-black sibling tree
        def rec(i):
            if i == FREE or i >= len(self.entries):
                return
            name, typ, l, r, c, st, sz = self.entries[i]
            rec(l)
            order.append(i)
            rec(r)
        rec(idx)
        for i in order:
            name, typ, l, r, c, st, sz = self.entries[i]
            path = prefix + [name]
            self.paths[tuple(path)] = i
            if typ == 1:
                self._walk(c, path)

    def listdir(self, streams=True, storages=False):
        return [list(p) for p, i in self.paths.items()
                if (self.entries[i][1] == 2 and streams) or (self.entries[i][1] == 1 and storages)]

    def exists(self, p):
        return tuple(p.split("/")) in self.paths

    def openstream(self, p):
        name, typ, l, r, c, st, sz = self.entries[self.paths[tuple(p.split("/"))]]
        if sz < self.cutoff:
            out, s = [], st
            while s < 0xFFFFFFFA:
                out.append(self.ministream[s * self.mss:(s + 1) * self.mss])
                s = self.minifat[s]
            data = b"".join(out)
        else:
            data = self._chain(st, self.fat)
        return io.BytesIO(data[:sz])

    def close(self):
        self.d = b""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

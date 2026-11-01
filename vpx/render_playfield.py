"""Rebuild the playfield picture from the VLM light-map atlas (see vpx/README.md)."""
import struct,zlib,sys,numpy as np
from PIL import Image
sys.path.insert(0,sys.argv[5])   # Stern-SAM-Decryption tools/vpx
import vpx_extract as vx
Image.MAX_IMAGE_PIXELS=None
# usage: render_playfield.py ATLAS.webp SCALE PFMESH.bin OUT.png SAM_TOOLS_VPX_DIR
# PFMESH.bin = the playfield_mesh item stream (GameStg/GameItemN whose NAME is playfield_mesh)
d=open(sys.argv[3],'rb').read()
r={t:p for t,p,o in vx.records(d,4)}
n=struct.unpack('<i',r['M3VN'])[0]
V=np.frombuffer(zlib.decompress(r['M3CX']),dtype='<f4').reshape(n,8)
I=np.frombuffer(zlib.decompress(r['M3CI']),dtype='<u2').reshape(-1,3)
atlas=Image.open(sys.argv[1]).convert("RGB"); A=np.asarray(atlas).astype(np.float32)
H,W=A.shape[:2]
S=float(sys.argv[2]); OW,OH=int(952*S),int(2115*S)
out=np.zeros((OH,OW,3),np.float32); zbuf=np.full((OH,OW),-1e9,np.float32)
for tri in I:
    p=V[tri]
    if p[:,5].mean()<0.5: continue
    x=-p[:,0]*S; y=-p[:,1]*S  # rotate 180 deg
    x0,x1=int(max(0,np.floor(x.min()))),int(min(OW-1,np.ceil(x.max())))
    y0,y1=int(max(0,np.floor(y.min()))),int(min(OH-1,np.ceil(y.max())))
    if x1<x0 or y1<y0: continue
    gx,gy=np.meshgrid(np.arange(x0,x1+1)+0.5,np.arange(y0,y1+1)+0.5)
    den=(y[1]-y[2])*(x[0]-x[2])+(x[2]-x[1])*(y[0]-y[2])
    if abs(den)<1e-9: continue
    l0=((y[1]-y[2])*(gx-x[2])+(x[2]-x[1])*(gy-y[2]))/den
    l1=((y[2]-y[0])*(gx-x[2])+(x[0]-x[2])*(gy-y[2]))/den
    l2=1-l0-l1
    m=(l0>=-1e-4)&(l1>=-1e-4)&(l2>=-1e-4)
    if not m.any(): continue
    z=l0*p[0,2]+l1*p[1,2]+l2*p[2,2]
    u=(l0*p[0,6]+l1*p[1,6]+l2*p[2,6])*W-0.5; v=(l0*p[0,7]+l1*p[1,7]+l2*p[2,7])*H-0.5
    ui=np.clip(np.round(u),0,W-1).astype(int); vi=np.clip(np.round(v),0,H-1).astype(int)
    sub=zbuf[y0:y1+1,x0:x1+1]; upd=m&(z>=sub)
    sub[upd]=z[upd]; out[y0:y1+1,x0:x1+1][upd]=A[vi[upd],ui[upd]]
print("coverage",(zbuf>-1e8).mean())
a=out/255; hi=np.percentile(a[a.sum(2)>0.05],99.5)
Image.fromarray((np.clip(a/hi,0,1)**0.55*255).astype(np.uint8)).save(sys.argv[4])   # brighten the dark-room bake

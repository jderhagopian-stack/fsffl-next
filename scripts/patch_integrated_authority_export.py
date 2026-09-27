from __future__ import annotations
import argparse, hashlib
from pathlib import Path

def sha(p):
    h=hashlib.sha256();h.update(Path(p).read_bytes());return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    s=args.source.read_text()
    original=s

    a='r={"season":season,"horizon":h,"position":e.position,'
    b='r={"season":season,"source_season":season,"player_id":e.player_id,"horizon":h,"position":e.position,"source_points":float(x.points),"current_state":cur,'
    if s.count(a)!=1:raise RuntimeError(f"metadata patch anchor count {s.count(a)}")
    s=s.replace(a,b)

    a2='   r[pref+"path"]=path;r[pref+"persist"]=1-p["out"];'
    b2='   r[pref+"path"]=path\n   for _s in STATES:r[pref+"p_"+_s]=p[_s]\n   if pref in ("i1_","i2_"):\n    _bm=B["I1" if pref=="i1_" else "I2"]["means"]\n    for _s in STATES:r[pref+"mean_"+_s]=max(0.0,float(_bm.g(e.position,h,_s)))\n   r[pref+"persist"]=1-p["out"];'
    if s.count(a2)!=1:raise RuntimeError(f"probability patch anchor count {s.count(a2)}")
    s=s.replace(a2,b2)

    args.output.write_text(s)
    print("source_sha256",sha(args.source))
    print("patched_sha256",sha(args.output))
    print("metadata_only_patch", len(s)-len(original))

if __name__=="__main__":main()

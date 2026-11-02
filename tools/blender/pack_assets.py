"""Pack baked GLBs as gzip+base64 text (<name>.glb.txt) so static hosts that
only serve text/web types (e.g. Claude artifacts) can ship them."""
import base64, gzip, pathlib, sys
d = pathlib.Path(sys.argv[1])
for glb in sorted(d.glob("*.glb")):
    out = glb.with_suffix(".glb.txt")
    out.write_text(base64.b64encode(gzip.compress(glb.read_bytes(), 9, mtime=0)).decode())
    print(f"{glb.name:18s} {glb.stat().st_size/1024:7.0f} KB -> {out.stat().st_size/1024:7.0f} KB")

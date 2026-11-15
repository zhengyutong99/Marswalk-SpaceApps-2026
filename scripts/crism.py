"""Real mineral map from CRISM MTRDR browse products (PDS Geosciences node, found via the ODE REST API).
Browse composites used (Viviano-Beck et al. 2014 summary parameters, 8-bit stretched, 255 = no data):
  CAR: R=D2300 (Fe/Mg clay), G=BD2500_2 (carbonate), B=BD1900_2 (hydration)
  MAF: R=OLINDEX3 (olivine), G=LCPINDEX2 (low-Ca pyroxene), B=HCPINDEX2 (high-Ca pyroxene)
  PHY: R=D2300 (Fe/Mg clay), G=D2200 (Al clay), B=BD1900R2 (hydration)
Each product is reprojected onto the site's 257x257 lon/lat grid; the strongest normalised signature wins.
  usage: venv/bin/python -I scripts/crism.py <site> <data dir> <dir with *_br{car,maf,phy}j_mtr3.img/.hdr> <product ids in priority order...>
  output: data/<site>_crism.u8  (0 no coverage, 1 clay, 2 carbonate, 3 olivine, 4 pyroxene, 5 no strong signature)"""
import sys, json, numpy as np, rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds
site, data, src, ids = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
meta = json.load(open(f'{data}/{site}_meta.json')); N = meta['N'] + 1
(lo0, lo1), (la0, la1) = meta['lon_range'], meta['lat_range']
LONLAT = '+proj=longlat +R=3396190 +no_defs'
# grid cell centres at j*C -> extend bounds half a cell so pixel centres line up with grid vertices
dl, dla = (lo1 - lo0) / (N - 1) / 2, (la1 - la0) / (N - 1) / 2
dst_t = from_bounds(lo0 - dl, la0 - dla, lo1 + dl, la1 + dla, N, N)
def warp(path):
    with rasterio.open(path) as s:
        out = np.full((3, N, N), 255, np.uint8)
        for b in range(3):
            reproject(rasterio.band(s, b + 1), out[b], src_nodata=255, dst_nodata=255, dst_transform=dst_t, dst_crs=LONLAT, resampling=Resampling.bilinear)
    return out.astype(np.float64)
cls = np.zeros((N, N), np.uint8); used = []
for pid in ids:
    car, maf, phy = (warp(f'{src}/{pid}_br{k}j_mtr3.img') for k in ('car', 'maf', 'phy'))
    valid = (car[0] < 255) & (maf[0] < 255) & (phy[0] < 255) & ((car.sum(0) + maf.sum(0)) > 0)
    if not valid.any(): continue
    def norm(a):   # stretch each parameter within this scene
        v = a[valid]; lo, hi = np.percentile(v, [50, 99]); return np.clip((a - lo) / max(1, hi - lo), 0, 1)
    score = np.stack([np.maximum(norm(car[0]), norm(phy[0])) * .9,   # Fe/Mg clay (D2300)
                      norm(car[1]),                                      # carbonate (BD2500)
                      norm(maf[0]),                                      # olivine
                      np.maximum(norm(maf[1]), norm(maf[2])) * .8])      # pyroxene
    c = score.argmax(0) + 1; c[score.max(0) < .35] = 5
    take = valid & (cls == 0); cls[take] = c[take]; used.append(pid)
    print(pid, 'adds coverage %.1f%%' % (100 * take.mean()))
cls.tofile(f'{data}/{site}_crism.u8')
meta['crism'] = used; json.dump(meta, open(f'{data}/{site}_meta.json', 'w'), indent=1)
print('coverage %.1f%%' % (100 * (cls > 0).mean()), 'classes', np.bincount(cls.ravel(), minlength=6))

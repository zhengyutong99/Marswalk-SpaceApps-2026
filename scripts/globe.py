"""Global Mars textures for the site-selector globe (equirectangular, 2048x1024, lon -180..180).
  colour : MOLA elevation colour blended with THEMIS day IR (USGS 'MolaThemis50BlendPalette'), read from its overview
  albedo : MGS TES bolometric albedo (7.4 km/px), tinted, for a natural-looking globe
usage: venv/bin/python scripts/globe.py data   (do NOT set GDAL_DISABLE_READDIR_ON_OPEN: the overviews live in a sibling .ovr)"""
import sys, numpy as np, rasterio
from rasterio.enums import Resampling
from PIL import Image
out = sys.argv[1]; W, H = 2048, 1024
B = '/vsicurl/https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/'
with rasterio.open(B + 'Mars_MGS_MolaThemis50BlendPalette_clon0_512ppd.tif') as d:
    a = d.read(1, out_shape=(H, W), resampling=Resampling.nearest)
    cmap = d.colormap(1)
lut = np.array([cmap.get(i, (0, 0, 0, 255))[:3] for i in range(256)], np.uint8)
Image.fromarray(lut[a]).save(out + '/globe_mola.jpg', quality=88)
with rasterio.open(B + 'Mars_MGS_TES_Albedo_mosaic_global_7410m.tif') as t:
    al = t.read(1, out_shape=(H, W), resampling=Resampling.bilinear, masked=True).astype(np.float64)
    print('albedo', t.width, t.height, t.dtypes, float(al.min()), float(al.max()))
al = al.filled(np.nanmedian(al)); lo, hi = np.percentile(al, [1, 99]); g = np.clip((al - lo) / (hi - lo), 0, 1)
# tint: dark basalt -> brown, bright dust -> butterscotch
dark, bright = np.array([60, 38, 28]), np.array([226, 150, 96])
rgb = dark + (bright - dark) * g[..., None] ** 0.9
Image.fromarray(rgb.astype(np.uint8)).save(out + '/globe_albedo.jpg', quality=88)
print('ok')

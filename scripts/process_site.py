"""Build the web-demo grids for one landing site from public USGS analysis-ready data.
Only the needed tiles of the Cloud-Optimized GeoTIFFs are streamed (HTTP range requests).

  GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR venv/bin/python scripts/process_site.py <site> data <previewdir>

Outputs (data/<site>_*):
  dem.f32     257x257 float32, elevation (m, Mars 2015 sphere), 10 m spacing
  rough.u8    90th percentile of 1 m slope (deg) per 10 m cell   (HiRISE DTM)
  albedo.u8   stretched HiRISE RED brightness
  themis.u8   THEMIS night-time IR brightness (100 m/px, qualitative thermal-inertia proxy), upsampled
  ortho.jpg   2048x2048 HiRISE RED ortho, north up
  meta.json   extent, lon/lat range, landing position (world metres: +x east, +z south)
"""
import sys, json, math, numpy as np, rasterio
from rasterio.windows import Window, from_bounds
from rasterio.enums import Resampling
from rasterio.warp import transform as warp_xy
from PIL import Image, ImageDraw

HI = 'https://astrogeo-ard.s3-us-west-2.amazonaws.com/mars/mro/hirise/controlled/dtm/'
TH = 'https://astrogeo-ard.s3.us-west-2.amazonaws.com/mars/mo/themis/controlled_mosaics/'
SITES = {
    'jezero': dict(folder='ESP_045994_1985_ESP_046060_1985', dtm='DTEEC_045994_1985_046060_1985_U01', ortho='ESP_045994_1985_RED_C_01_ORTHO',
                   center=(77.43686, 18.46335), landing=(77.4508, 18.4447), themis='mc13_syrtis_major_nir'),
    'gale': dict(folder='ESP_018854_1755_ESP_018920_1755', dtm='DTEEC_018854_1755_018920_1755_U01', ortho='ESP_018854_1755_RED_C_01_ORTHO',
                 center=(137.3880, -4.6850), landing=(137.3880, -4.6850), themis='mc23_aeolis_nir'),
}
site, outdir, prevdir = sys.argv[1], sys.argv[2], sys.argv[3]
S = SITES[site]
if len(sys.argv) > 5: S['center'] = (float(sys.argv[4]), float(sys.argv[5]))
N = 256; WM = 2560.0; R = 3396190.0
LONLAT = '+proj=longlat +R=3396190 +no_defs'
pre = f'{outdir}/{site}_'

with rasterio.open('/vsicurl/' + HI + S['folder'] + '/' + S['dtm'] + '.tif') as d:
    res = d.res[0]; px = int(round(WM / res))
    xs, ys = warp_xy(LONLAT, d.crs, [S['center'][0]], [S['center'][1]])
    r, c = d.index(xs[0], ys[0])
    win = Window(c - px // 2, r - px // 2, px, px)
    z = d.read(1, window=win, masked=True, boundless=True).astype(np.float64)
    print('dtm window', z.shape, 'masked %', round(100 * float(z.mask.mean()), 2))
    bounds = d.window_bounds(win); dcrs = d.crs
    z = z.filled(np.nan)
if np.isnan(z).any():   # fill small gaps from the nearest valid row/col average
    m = np.isnan(z); z[m] = np.nanmedian(z)

def sample(a, n):
    s = (a.shape[0] - 1) / n
    t = np.arange(n + 1) * s; i0 = np.floor(t).astype(int).clip(0, a.shape[0] - 2); f = t - i0
    r = a[i0] * (1 - f)[:, None] + a[i0 + 1] * f[:, None]
    return r[:, i0] * (1 - f)[None, :] + r[:, i0 + 1] * f[None, :]
H = sample(z, N)
gy, gx = np.gradient(z, res)
SL = np.degrees(np.arctan(np.hypot(gx, gy)))
blk = px / N; rough = np.zeros((N + 1, N + 1))
for i in range(N + 1):
    r0 = int(max(0, i * blk - blk / 2)); r1 = int(min(px, i * blk + blk / 2 + 1)); rows = SL[r0:r1]
    for j in range(N + 1):
        c0 = int(max(0, j * blk - blk / 2)); c1 = int(min(px, j * blk + blk / 2 + 1))
        rough[i, j] = np.nanpercentile(rows[:, c0:c1], 90)

with rasterio.open('/vsicurl/' + HI + S['folder'] + '/' + S['ortho'] + '.tif') as o:
    ow = o.window(*bounds)
    img = o.read(1, window=ow, out_shape=(2048, 2048), resampling=Resampling.average, boundless=True, fill_value=0).astype(np.float64)
m = img > 0; lo, hi = np.percentile(img[m], [0.5, 99.5])
g = np.clip((img - lo) / (hi - lo), 0, 1); g[~m] = np.median(g[m])
Image.fromarray((g * 255).astype(np.uint8)).save(pre + 'ortho.jpg', quality=88)
alb = sample(g, N)

# lon/lat of the crop corners (DTM CRS -> sphere lon/lat)
left, bottom, right, top = bounds
(lon0, lon1), (lat0, lat1) = warp_xy(dcrs, LONLAT, [left, right], [bottom, top])

# THEMIS night IR (bright at night = warm = high thermal inertia: rock / bedrock; dark = loose fine sand)
with rasterio.open('/vsicurl/' + TH + S['themis'] + '/' + S['themis'] + '.tif') as t:
    tx, ty = warp_xy(LONLAT, t.crs, [lon0, lon1], [lat0, lat1])
    tw = from_bounds(tx[0], ty[0], tx[1], ty[1], t.transform)
    th = t.read(1, window=tw, out_shape=(N + 1, N + 1), resampling=Resampling.bilinear).astype(np.float64)
    print('themis native px', round(tw.width, 1), 'x', round(tw.height, 1))
tl, thh = np.percentile(th[th > 0], [2, 98]); th = np.clip((th - tl) / max(1, thh - tl), 0, 1)

H.astype('<f4').tofile(pre + 'dem.f32')
np.clip(rough, 0, 255).astype(np.uint8).tofile(pre + 'rough.u8')
np.clip(alb * 255, 0, 255).astype(np.uint8).tofile(pre + 'albedo.u8')
np.clip(th * 255, 0, 255).astype(np.uint8).tofile(pre + 'themis.u8')

def world(lon, lat):
    return (-WM / 2 + (lon - lon0) / (lon1 - lon0) * WM, -WM / 2 + (lat1 - lat) / (lat1 - lat0) * WM)
meta = dict(site=site, W=WM, N=N, res_src=res, product=S['dtm'], ortho=S['ortho'], themis=S['themis'],
            lon_range=[lon0, lon1], lat_range=[lat0, lat1],
            hmin=float(np.nanmin(H)), hmax=float(np.nanmax(H)), landing=world(*S['landing']))
json.dump(meta, open(pre + 'meta.json', 'w'), indent=1)
print(json.dumps(meta, indent=1))

pv = Image.fromarray((g * 255).astype(np.uint8)).convert('RGB').resize((1024, 1024))
dr = ImageDraw.Draw(pv); k = 1024 / WM
for wv in range(-1250, 1300, 250):
    p = (wv + WM / 2) * k; col = (0, 200, 255) if wv % 500 == 0 else (0, 90, 120)
    dr.line([(p, 0), (p, 1024)], fill=col); dr.line([(0, p), (1024, p)], fill=col)
    if wv % 500 == 0: dr.text((p + 2, 2), str(wv), fill=(255, 255, 0)); dr.text((2, p + 2), str(wv), fill=(255, 255, 0))
lx, lz = meta['landing']; cx, cz = (lx + WM / 2) * k, (lz + WM / 2) * k
dr.ellipse([cx - 8, cz - 8, cx + 8, cz + 8], outline=(255, 0, 0), width=3)
pv.save(f'{prevdir}/{site}_pick.png')
Image.fromarray((th * 255).astype(np.uint8)).resize((512, 512)).save(f'{prevdir}/{site}_themis.png')
hs = (np.clip((H - np.nanmin(H)) / (np.nanmax(H) - np.nanmin(H)), 0, 1) * 255).astype(np.uint8)
Image.fromarray(hs).resize((512, 512)).save(f'{prevdir}/{site}_height.png')

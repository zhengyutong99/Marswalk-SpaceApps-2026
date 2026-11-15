"""Pin real rover photos to the map.
Waypoints (sol, lat, lon, rover yaw) come from the NASA MMGIS traverse JSON; images come from the public
raw-image API (mars.nasa.gov/rss/api). For each waypoint inside the site crop we keep a few horizon-looking
colour frames taken at that site/drive.   usage: fetch_photos.py <waypoints.json> <meta.json> <outdir> <mission m20|msl> <maxStops>"""
import sys, json, math, os, urllib.request, time
wp_path, meta_path, outdir, mission, max_stops = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
meta = json.load(open(meta_path)); os.makedirs(outdir, exist_ok=True)
(lo0, lo1), (la0, la1), W = meta['lon_range'], meta['lat_range'], meta['W']
def world(lon, lat): return (-W/2 + (lon-lo0)/(lo1-lo0)*W, -W/2 + (la1-lat)/(la1-la0)*W)
fs = [f['properties'] for f in json.load(open(wp_path))['features']]
inside = [p for p in fs if la0 < p['lat'] < la1 and lo0 < p['lon'] < lo1]
# keep stops at least 60 m apart so pins spread over the map
stops = []
for p in inside:
    x, z = world(p['lon'], p['lat'])
    if all(math.hypot(x-s['x'], z-s['z']) > 60 for s in stops): stops.append(dict(p, x=x, z=z))
if len(stops) > max_stops:
    step = len(stops) / max_stops; stops = [stops[int(i*step)] for i in range(max_stops)]
cat = {'m20': 'mars2020', 'msl': 'msl'}[mission]
GOOD = {'m20': ('NAVCAM_LEFT', 'MCZ_LEFT', 'FRONT_HAZCAM_LEFT_A'), 'msl': ('NAV_LEFT_B', 'NAV_LEFT_A', 'MAST_LEFT', 'MAST_RIGHT')}[mission]
def num(v):
    try: return float(v)
    except Exception: return 0.0
def get(url):
    for a in range(3):
        try:
            with urllib.request.urlopen(url, timeout=40) as r: return r.read()
        except Exception as e: err = e; time.sleep(2)
    raise err
out = []
for s in stops:
    sol = s['sol']
    if mission == 'm20':
        ims = []
        for pg in range(6):
            api = f"https://mars.nasa.gov/rss/api/?feed=raw_images&category=mars2020&feedtype=json&num=100&page={pg}&order=sol%20desc&condition_2={sol}:sol:gte&condition_3={sol}:sol:lte"
            batch = json.loads(get(api))['images']; ims += batch
            if len(batch) < 100: break
        rows = [dict(cam=i['camera']['instrument'], el=num(i['extended'].get('mastEl')), az=num(i['extended'].get('mastAz')),
                     url=i['image_files'].get('medium') or i['image_files'].get('large'), site=i.get('site'), drive=i.get('drive'),
                     color='_EBY_' in (i['image_files'].get('medium') or '') or 'ECM' in (i['image_files'].get('medium') or ''), t=i.get('date_taken_mars'), dim=i['extended'].get('dimension', '(0,0)')) for i in ims]
    else:
        raw = []
        for pg in range(8):
            api = f"https://mars.nasa.gov/api/v1/raw_image_items/?order=sol%20desc&per_page=100&page={pg}&condition_1=msl:mission&condition_2={sol}:sol:in"
            d = json.loads(get(api)); raw += d.get('items', [])
            if not d.get('more'): break
        ims = [i for i in raw if (i.get('extended') or {}).get('sample_type') == 'full']
        rows = [dict(cam=i.get('instrument'), el=-5.0, az=num((i.get('extended') or {}).get('mast_az')),
                     url=i.get('https_url') or i.get('url'), site=i.get('site'), drive=i.get('drive'), color=i.get('instrument','').startswith('MAST'), t=i.get('date_taken_mars'), dim='(1024,1024)') for i in ims]
    site, drive = (int(v) for v in s['RMC'].split('_'))
    def full(r):   # full frames only (no thumbnails / strips / subframes)
        try: w, h = (int(v) for v in r['dim'].strip('()').split(','))
        except Exception: return False
        return w >= 640 and h / w > .55
    cand = [r for r in rows if r['cam'] in GOOD and r['url'] and -28 < r["el"] < 10 and full(r) and (r['site'] in (None, site))]
    cand.sort(key=lambda r: (r['drive'] != drive, abs(r['el'] + 6)))
    picked, azs = [], []
    for r in cand:
        if all(abs(((r['az'] - a + 180) % 360) - 180) > 50 for a in azs): picked.append(r); azs.append(r['az'])
        if len(picked) == 2: break
    for n, r in enumerate(picked):
        fn = f"{mission}_sol{sol:04d}_{n}.jpg"
        try: open(os.path.join(outdir, fn), 'wb').write(get(r['url']))
        except Exception as e: print('skip', r['url'], e); continue
        out.append(dict(file=fn, sol=sol, cam=r['cam'], x=round(s['x'], 1), z=round(s['z'], 1), lat=s['lat'], lon=s['lon'],
                        heading=round((s.get('yaw', 0) + r['az']) % 360, 1) if mission == 'm20' else None, el=r['el'], src=r['url'], mars_time=r['t']))
    print('sol', sol, 'images', len(rows), 'picked', len(picked))
json.dump(out, open(os.path.join(outdir, 'photos.json'), 'w'), indent=1)
print('total', len(out))

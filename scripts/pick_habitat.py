"""Pick a habitat spot for a site: flat, firm ground with the best radio line of sight.
Score = line of sight to the science targets (weighted ×3) + share of the ground within 1.3 km in view,
minus a small penalty for distance to the targets. Candidates: slope < 6°, low 1 m roughness, not dark sand, at least 200 m from every stop.
  usage: python3 scripts/pick_habitat.py <site> [--write]   (needs numpy; --write updates data/sites.json)"""
import sys, json, numpy as np
site = sys.argv[1]; N = 257; C = 10.0; pre = f'data/{site}_'
H = np.fromfile(pre + 'dem.f32', '<f4').reshape(N, N).astype(np.float64)
R = np.fromfile(pre + 'rough.u8', 'u1').reshape(N, N).astype(float)
A = np.fromfile(pre + 'albedo.u8', 'u1').reshape(N, N).astype(float)
gy, gx = np.gradient(H, C); S = np.degrees(np.arctan(np.hypot(gx, gy)))
sites = json.load(open('data/sites.json')); T = [t for t in sites[site]['targets']]
X = np.arange(N) * C - 1280
w = lambda v: int(round((v + 1280) / C))           # world metres -> grid index
dark = np.percentile(A, 25)

# sample points: every 5th cell within 1.3 km of the candidate, plus every target
grid = [(i, j) for i in range(0, N, 5) for j in range(0, N, 5)]
tgt = [(w(t['z']), w(t['x']), t['on']) for t in T]
steps = np.linspace(0, 1, 72)[1:-1]
def visible(ci, cj, pts):
    pts = np.array(pts, float)
    ii = np.rint(ci + (pts[:, 0:1] - ci) * steps).astype(int); jj = np.rint(cj + (pts[:, 1:2] - cj) * steps).astype(int)
    h0 = H[ci, cj] + 6; h1 = H[pts[:, 0].astype(int), pts[:, 1].astype(int)] + 2
    line = h0 + (h1[:, None] - h0) * steps
    return (H[ii, jj] <= line).all(axis=1)

best = None
for ci in range(20, N - 20, 4):
    for cj in range(20, N - 20, 4):
        if S[ci, cj] > 6 or R[ci, cj] > 10 or A[ci, cj] < dark: continue
        if S[ci - 2:ci + 3, cj - 2:cj + 3].max() > 9: continue      # the whole pad must be flat
        if min(np.hypot(i - ci, j - cj) * C for i, j, _ in tgt) < 200: continue   # keep the base off the science stops
        near = [(i, j) for i, j in grid if np.hypot(i - ci, j - cj) * C < 1300]
        area = visible(ci, cj, near).mean() if near else 0
        tv = visible(ci, cj, [(i, j) for i, j, _ in tgt]); wts = np.array([2.0 if on else 1.0 for *_, on in tgt])
        tscore = (tv * wts).sum() / wts.sum()
        dist = np.mean([np.hypot(i - ci, j - cj) * C for i, j, on in tgt if on] or [0])
        score = 3 * tscore + area - dist / 4000
        if best is None or score > best[0]: best = (score, ci, cj, area, tscore, dist)
score, ci, cj, area, tscore, dist = best
x, z = X[cj], X[ci]
print(f'{site}: habitat ({x:.0f}, {z:.0f}) slope {S[ci, cj]:.1f}° · targets in view {tscore * 100:.0f}% (weighted) · ground in view {area * 100:.0f}% · mean distance {dist:.0f} m')
if '--write' in sys.argv:
    sites[site]['base'] = [int(x), int(z)]
    json.dump(sites, open('data/sites.json', 'w'), indent=1)

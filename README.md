# Marswalk — Mars EVA planner

NASA Space Apps Challenge 2026 · *Interplanetary Survival Guide: Martian Map*

Marswalk helps an astronaut and their rover partner plan a safe excursion (EVA) on real Martian terrain, then rehearse it in first person through a helmet HUD.

1. **Pick a site** on a 3D Mars globe (`index.html`).
2. **Plan** in the site planner (`planner.html?site=jezero` or `?site=gale`): choose science stops, rover or walking, and a start time. The A* route planner shows distance, duration, O₂ margin, radiation dose, risk of getting stuck in sand, comms blackout, and the walk-back limit, then gives a GO / CAUTION / NO-GO verdict.
3. **Rehearse** the route in first person, with day and night, shadows, hazards and resource limits, or drop the pegman anywhere for a free street-view preview. Each rehearsal ends with a debrief and score.

## Run it

It is a static site: no build step and no backend. Three.js loads from a CDN.

```bash
python3 -m http.server 8791
# open http://localhost:8791
```

## Real data vs model

| Feature | Data | Status |
|---|---|---|
| Terrain, slope, roughness | HiRISE DTM 1 m (UA / USGS) | real |
| Surface image | HiRISE RED ortho | real |
| Soft soil / thermal inertia | THEMIS night-time IR, 100 m (Mars Odyssey) + HiRISE albedo | real, qualitative |
| Minerals | CRISM MTRDR summary products (MRO) | real, qualitative |
| Rover photos | Perseverance / Curiosity raw images at their traverse stops | real |
| Comms line of sight, walk-back time, radiation shelter | computed from the DTM | derived |
| Globe | MOLA + THEMIS blend, TES albedo | real |
| Mars time, sun position | Mars24 algorithm (Allison & McEwen 2000) | computed |
| Temperature, wind, dust, pressure | fitted to published MEDA / REMS ranges | **model** |
| Rock positions | random, but density follows real 1 m roughness | **model** |
| Speeds, O₂ use, battery, sand-trap odds | engineering estimates | **model** |

## Controls (first person)

Drag to look · click the ground to move there · W/S/A/D to move · ←/→ to turn · Shift to go faster · V to switch rover/walk · P for autopilot · T for time (pause in street view, speed ×1/×5/×20 in rehearsal) · [ ] or ⏪ ⏩ to jump an hour · 1–4 for minimap filters (image, hazards, comms, walk-back) · C for the cuff checklist · N for a field note · F to open a nearby rover photo · M for the site map · H for controls · Esc for the pause menu.

The 📖 Manual button in the planner lists every rule and limit the simulation uses (O₂, batteries, slope limits, sand-trap odds, night, comms, walk-back, radiation, scoring).

## Share a plan

The 🔗 button copies a link that encodes the site, stops (including custom ones), mobility, route priority, payload and start time, e.g. `planner.html?site=gale&mob=walk&prof=safe&pay=kit&t=9.5&stops=G1.G2`.

## Project layout

```
index.html          Mars globe site selector
planner.html        planner + first-person rehearsal (Three.js, one file)
data/               generated site packages (see data/README.md)
scripts/
  process_site.py   HiRISE DTM/ortho + THEMIS → site grids
  crism.py          CRISM browse products → mineral classes
  fetch_photos.py   rover waypoints + raw image API → photo pins
  globe.py          global textures
```

`data/README.md` lists every source product and the commands to regenerate the data. `docs/PROJECT.md` explains how the project maps to the challenge.

## Credits

NASA/JPL-Caltech, University of Arizona (HiRISE), ASU (THEMIS), JHU-APL (CRISM), MSSS and ASU (rover cameras), USGS Astrogeology (analysis-ready data and mosaics), PDS Geosciences Node (ODE).

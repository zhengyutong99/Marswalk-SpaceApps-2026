# Marswalk: project write-up

NASA Space Apps Challenge 2026 · **Interplanetary Survival Guide: Martian Map** (Intermediate · Human Exploration, Mars, Software)

## 1. The problem

The challenge asks for *"a map, tool, or interface a Mars astronaut could use during a surface exploration mission, using NASA data and tools."* Existing tools such as JPL Mars Trek are built for regional and global views. They don't zoom in on the few square kilometres an astronaut covers in one excursion, and they don't answer the crew's real questions:

- Can I get there and back safely, on foot or by rover?
- How much O₂, battery and radiation dose will it cost?
- Where could I get stuck, lose contact, or be caught by a solar storm?
- What will it look like when I arrive, and what science is there?

## 2. Our answer

**Marswalk** is a planning tablet plus a helmet HUD for an astronaut and their rover partner:

1. **Choose a site** on a 3D Mars globe. Two sites are fully built: Jezero (Perseverance) and Gale (Curiosity).
2. **Plan** an EVA on real 1 m terrain. Pick science stops, rover or walking, payload and start time. A route planner draws the safest or fastest path and returns a **GO / CAUTION / NO-GO** verdict, with a reason for each risk.
3. **Rehearse** the route in first person through the helmet HUD. Day and night, hazards and resource limits all apply, and real rover photos show what each stop looks like. Each rehearsal ends with a scored debrief.
4. **Share** the plan as a link, or print an EVA cuff card.

## 3. How it meets the challenge

| Challenge text | What Marswalk does |
|---|---|
| "a layered, integrated view of a location or route" | 8 data layers draped on 3D terrain, grouped as Hazards, Safety, and Science; the same data appears as minimap filters in first person |
| "pulls together data from multiple NASA science missions" | MRO HiRISE (terrain, image), MRO CRISM (minerals), Mars Odyssey THEMIS (thermal inertia), MGS MOLA and TES (globe), MSL and Mars 2020 rover images and traverses, MSL RAD (dose baseline), MEDA/REMS (climate ranges) |
| "at least three kinds of data: optical, thermal, spectral, topographic… radiation…" | optical (HiRISE), thermal (THEMIS night IR), spectral (CRISM), topographic (HiRISE DTM), radiation (RAD baseline + terrain shielding), atmospheric (sun, temperature, dust model) |
| "hyperlocalized areas astronauts will target" | 2.56 × 2.56 km sites at 1 m source resolution (10 m planning grid) |
| "NASA's first priority is always astronaut safety" | GO/NO-GO verdict, O₂ margin, battery budget, chance of getting stuck in sand, comms line of sight, walk-back limit, night penalties |
| "you might include space weather data" | Solar-particle-event mode: routes prefer terrain shelter; a "shelter drill" injects an alert mid-EVA and points to the nearest shelter |
| "spacesuits… carrying scientific equipment… impact their mobility" | Payload choice (light / sampling kit / core drill) changes walking speed, O₂ use and battery |
| "a route map… avoiding significant obstacles such as large rock formations" | A* route planner on slope, 1 m roughness and soft soil; rocks are physical colliders in first person; compass shows hazards ahead |
| "a display inside the habitat… a tablet… a HUD on the helmet visor" | Planner = tablet, first person = helmet HUD, globe = habitat display |
| "a tool or system that generates maps of different locations" | `scripts/process_site.py` builds a new site from any HiRISE DTM in the USGS catalogue; the globe shows 7 more candidate sites |
| "predicted data and conditions for a future time frame" | Real Mars time at each site right now (Mars24), sunrise/sunset, a forecast for the sol, and the recommended EVA window |
| "imagery taken by NASA's Mars surface missions… point-of-view images" | 43 real Perseverance / Curiosity raw images pinned where the rover took them; a preview opens as you approach each stop |
| "rovers or other robotic systems to help transport the crew and their tools" | Astronaut + rover partner: ride or walk, the Apollo-style walk-back rule if the rover fails, rover battery and sand traps |
| "astronauts use their critical thinking… apply context to observations" | Science card at each stop (CRISM mineral, thermal inertia, elevation) and geotagged field notes, collected in the debrief |

## 4. Data and sources

All data is public. It is processed by the scripts in `scripts/` and streamed from Cloud-Optimized GeoTIFFs (only the needed tiles are downloaded).

| Data | Product | Mission / instrument | Source |
|---|---|---|---|
| Terrain, slope, roughness (Jezero) | `DTEEC_045994_1985_046060_1985_U01` | MRO HiRISE | USGS Astrogeology STAC `mro_hirise_socet_dtms` |
| Terrain (Gale) | `DTEEC_018854_1755_018920_1755_U01` | MRO HiRISE | same |
| Surface images | `ESP_045994_1985_RED`, `ESP_018854_1755_RED` orthos | MRO HiRISE | same |
| Thermal inertia (qualitative) | THEMIS IR night mosaics `mc13_syrtis_major_nir`, `mc23_aeolis_nir` (100 m) | Mars Odyssey THEMIS | USGS STAC `mo_themis_controlled_mosaics` |
| Minerals | CRISM MTRDR browse products `FRT000047A3`, `FRT00005C5E` (Jezero); `FRT0000B6F1`, `FRT0000C0EF` (Gale) | MRO CRISM | PDS Geosciences Node via the ODE REST API |
| Rover photos | Raw images at traverse stops (16 Perseverance, 27 Curiosity) | Mars 2020, MSL | mars.nasa.gov raw image APIs + MMGIS waypoint JSON |
| Globe | `Mars_MGS_MolaThemis50BlendPalette`, `Mars_MGS_TES_Albedo` | MGS MOLA, Odyssey THEMIS, MGS TES | USGS Astrogeology mosaics |
| Radiation baseline | ~0.67 mSv/sol surface average | MSL RAD | published results |
| Climate ranges | air / ground temperature, pressure, dust | Mars 2020 MEDA, MSL REMS | published climatology |
| Mars time, sun position | Mars24 algorithm (Allison & McEwen 2000) | NASA GISS | computed in the browser |

### Real, derived, or model

- **Real:** terrain, images, THEMIS, CRISM, rover photos and their positions, Mars time and sun position.
- **Derived from real data:** slope, 1 m roughness, soft soil (THEMIS night IR + HiRISE albedo + slope), comms line of sight, walk-back time, radiation shelter (sky view).
- **Model / estimate:** temperature, wind, dust and pressure curves (fitted to MEDA/REMS ranges, not a live feed), speeds, O₂ and battery use, chance of getting stuck, rock positions (random, but their density follows real roughness).

The app labels each layer *REAL DATA* or *MODEL*, and the in-app Field Manual lists every rule.

## 5. How it works

**Site pipeline** (`scripts/process_site.py`, `crism.py`, `fetch_photos.py`, `globe.py`):

1. Crop a 2560 m window from the HiRISE DTM and ortho, then resample to a 257 × 257 grid (10 m).
2. Compute the 90th percentile of the 1 m slope inside each 10 m cell. This is the roughness, a proxy for boulders.
3. Sample the THEMIS night IR mosaic onto the same grid.
4. Reproject the CRISM summary browse products (D2300, BD2500, OLINDEX3, LCP/HCP index) and keep the strongest signature per cell.
5. Match rover waypoints inside the crop to raw images taken at the same site and drive.

**Planner** (`planner.html`, Three.js, no backend):

- **Cost field** per cell: slope², soft soil, roughness, plus a terrain-shelter term during an SPE. Cells beyond the slope or rock limit for the chosen mobility are impassable. The Safest profile keeps the slope limit 5° lower.
- **A\*** on an 8-neighbour grid between the stops (nearest-neighbour order), then the route is resampled every 4 m.
- **Budget along the route:** time, O₂ (metabolic rate depends on slope, sand and payload), battery (distance + heaters in the cold), dose (background + SPE × exposure), chance of getting stuck, comms coverage, time after sunset.
- **Walk-back limit:** Dijkstra from the habitat with suited walking speed. At every route point, walk-home time × 1.25 + 30 min must fit the remaining O₂. Segments that break this rule are drawn in red.
- **Comms:** line of sight from a 6 m mast to a 2 m antenna, traced over the DTM.

**First person:** the same terrain at true scale, the sun from Mars24, shadows, sky colour and stars. Rock and base colliders, sand traps, fail states, time warp, minimap filters, and a hazard-ahead strip on the compass. Rocks are split into 64 chunks, and only the chunks near the player and inside the view are drawn.

## 6. Limitations and next steps

- The weather is a climatology model. Next step: ingest MEDA/REMS time series or Mars Climate Database forecasts.
- CRISM and THEMIS are used qualitatively. Next step: quantitative THEMIS thermal inertia and CRISM MTRDR spectral parameters.
- Rock positions are procedural. Next step: boulder detection in 25 cm HiRISE images.
- Sites are separate 2.56 km tiles. Next step: quadtree streaming (MOLA → CTX → HiRISE) for a seamless planet.
- Two-astronaut (buddy) EVAs are not modelled.

## 7. Run it

```bash
python3 -m http.server 8791
# open http://localhost:8791
```

`data/README.md` lists the commands to regenerate every data file.

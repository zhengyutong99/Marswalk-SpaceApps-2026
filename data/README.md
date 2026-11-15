# Data

Everything here is generated from public NASA / USGS data by the scripts in `../scripts/`.
Only the needed tiles of each Cloud-Optimized GeoTIFF are streamed (HTTP range requests).

## Per site (`<site>` = `jezero`, `gale`)

| File | Content | Source |
|---|---|---|
| `<site>_dem.f32` | 257×257 Float32 LE, elevation (m, Mars 2015 sphere), 10 m spacing | HiRISE DTM (UA / USGS) |
| `<site>_rough.u8` | 90th percentile of the 1 m slope (deg) in each 10 m cell | HiRISE DTM |
| `<site>_albedo.u8` | stretched HiRISE RED brightness | HiRISE ortho |
| `<site>_ortho.jpg` | 2048×2048 HiRISE RED ortho, north up | HiRISE ortho |
| `<site>_themis.u8` | THEMIS night-time IR brightness (qualitative thermal inertia), 100 m upsampled | Mars Odyssey THEMIS controlled mosaics (USGS STAC) |
| `<site>_crism.u8` | mineral class: 1 Fe/Mg clay, 2 carbonate, 3 olivine, 4 pyroxene, 5 none | CRISM MTRDR browse products (PDS Geosciences, via ODE) |
| `<site>_meta.json` | extent, lon/lat range, products used | |
| `<site>/photos/` | real rover raw images pinned at traverse stops + `photos.json` | NASA MMGIS waypoints + mars.nasa.gov raw image API (NASA/JPL-Caltech) |

Sites:
- **Jezero**: DTM `DTEEC_045994_1985_046060_1985_U01`, 18.442–18.485°N, 77.415–77.458°E (Perseverance landing site → western delta front). CRISM `FRT000047A3`, `FRT00005C5E`.
- **Gale**: DTM `DTEEC_018854_1755_018920_1755_U01`, 4.664–4.707°S, 137.366–137.410°E (Bagnold dunes, Murray formation, Marias Pass). CRISM `FRT0000B6F1`, `FRT0000C0EF`.
- **Jezero delta front**: DTM `DTEEC_002387_1985_003798_1985_A01`, 18.447–18.491°N, 77.368–77.411°E (Perseverance sols 409–836).
- **Gale boxwork**: DTM `DTEEC_019698_1750_019988_1750_U01`, 4.780–4.824°S, 137.357–137.401°E (Curiosity sols 4414–4998, boxwork ridges).
- **Mawrth Vallis**: DTM `DTEEC_008469_2040_008825_2040_U01`, 23.837–23.880°N, 340.949–340.992°E (never visited; CRISM covers ~20 % of the crop).

The live Environment panel also reads the latest Curiosity REMS report (mars.nasa.gov weather feed) and NASA DONKI solar energetic particle events (api.nasa.gov, DEMO_KEY).

## Globe
- `globe_mola.jpg` – 2048×1024 MOLA elevation colour blended with THEMIS day IR (`Mars_MGS_MolaThemis50BlendPalette`, read from its overview)
- `globe_albedo.jpg` – MGS TES albedo, tinted
- `sites.json` – site list, targets, climate ranges (MEDA / REMS) used by the weather model

## Regenerate

    python3 -m venv venv && venv/bin/pip install rasterio numpy pillow
    GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR venv/bin/python scripts/process_site.py jezero data /tmp
    GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR venv/bin/python scripts/process_site.py gale data /tmp
    venv/bin/python scripts/globe.py data
    # CRISM: download the *_br{car,maf,phy}j_mtr3.img/.hdr browse files listed by the ODE REST API into a folder, then
    venv/bin/python -I scripts/crism.py jezero data <folder> frt000047a3_07 frt00005c5e_07
    # photos (waypoint JSON from https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_waypoints.json)
    python3 scripts/fetch_photos.py M20_waypoints.json data/jezero_meta.json data/jezero/photos m20 16

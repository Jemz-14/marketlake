# MarketLake — Ingestion (Phase 1: Bronze)

Python extractors that land raw market data into a local medallion **bronze**
lake as date-partitioned Parquet, using two patterns that carry over to the
cloud version:

- **Metadata-driven** — the ticker list lives in [`config/sources.json`](config/sources.json)
  (the control table). Adding a ticker is a data edit, not a code change.
- **Incremental** — a per-source/per-ticker high-water-mark means each run pulls
  only new dates and is safely re-runnable (idempotent).

## Sources

| Source | Module | Grain | Role |
|---|---|---|---|
| Daily OHLCV prices | `src/sources/prices.py` | one row / ticker / day | fact |
| Company fundamentals | `src/sources/fundamentals.py` | one row / ticker (daily snapshot) | dimension |
| FX rates | `src/sources/fx.py` | one row / date / currency pair | normalisation |

Output layout: `_lake/bronze/<source>/date=YYYY-MM-DD/…parquet`
Watermarks: `_lake/_state/watermarks.json`

---

## Run locally (Python)

```powershell
# from the repo root, with the venv active
cd ingestion
python extract.py                 # all sources, incremental
python extract.py --full-refresh  # ignore watermark, re-pull from default_start
python -m pytest -q               # unit tests
```

---

## Run with Docker

The image bundles Python + dependencies + the extractor. The lake is **not**
baked in — you mount a host folder to `/data`, so your data persists on disk
and incremental watermarks survive between runs.

### 1. Start Docker Desktop
Launch Docker Desktop and wait until it reports **Engine running**. Verify:
```powershell
docker info --format '{{.ServerVersion}}'
```

### 2. Build the image
```powershell
cd ingestion
docker build -t marketlake-ingest .
```

### 3. Run the job (mount the lake)
```powershell
docker run --rm -v "${PWD}\_lake:/data" marketlake-ingest
```
- `--rm` removes the container when it exits (the data lives in the mount, not the container).
- `-v "${PWD}\_lake:/data"` maps `ingestion\_lake` on your machine to `/data` inside the container.
- The image defaults `LAKE_ROOT=/data`, so output lands in your mounted `_lake\`.

Pass any `extract.py` flag after the image name:
```powershell
docker run --rm -v "${PWD}\_lake:/data" marketlake-ingest --sources fx --full-refresh
docker run --rm -v "${PWD}\_lake:/data" marketlake-ingest --end 2026-05-30 --log-level DEBUG
```

### 4. Verify
```powershell
Get-ChildItem _lake\bronze -Recurse -Filter *.parquet | Measure-Object   # count partition files
Get-Content _lake\_state\watermarks.json
```
Re-run step 3 — the second run should report near-zero new rows (the watermark
short-circuit), proving incremental + idempotent behaviour.

### Troubleshooting
- **`error during connect … dockerDesktopLinuxEngine`** → Docker Desktop isn't running. Start it (step 1).
- **Permission denied writing to `/data`** → ensure Docker Desktop → Settings → Resources → File Sharing includes your drive (local drives are shared by default on the WSL2 backend).
- **First build is slow** → it downloads the base image and wheels once; later builds reuse cached layers.

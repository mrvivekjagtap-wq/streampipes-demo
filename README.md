# StreamPipes 0.98.0 — local demo stack

Staged for the Jesco motor/pump monitoring evaluation. Files here are the official
Apache compose files, pulled from tag `release/0.98.0`.

## 0. Prerequisites

- A container runtime. **OrbStack** (lighter, ~1 GB, recommended on an 8 GB Mac) or Docker Desktop.
- **~10 GB free disk.** Images unpack to ~2.5 GB, plus the runtime's VM disk and volumes.
- Port **80** free (the UI binds host :80 → container :8088).

## 1. Start

```bash
cd ~/projects/uix/streampipes-local && docker compose up -d
```

First run pulls ~0.9 GB compressed. Then watch it come up:

```bash
docker compose ps && docker compose logs -f backend
```

Open <http://localhost> → setup wizard → install all pipeline elements →
create the admin user (or use `admin@streampipes.apache.org` / `admin`).

Stop / wipe:

```bash
docker compose down            # stop, keep data
docker compose down -v         # stop and delete all volumes (fresh start)
```

## 2. What the 6 containers are

| Container | Image | Role |
|---|---|---|
| `ui` | apachestreampipes/ui | Angular UI + nginx. **Host port 80** |
| `backend` | apachestreampipes/backend | Core: REST API, pipeline manager, auth |
| `extensions-all-iiot` | apachestreampipes/extensions-all-iiot | All bundled adapters/processors/sinks. Each pipeline element runs here |
| `couchdb` | couchdb:3.3.1 | **Metadata DB** — pipelines, adapters, users, dashboards, schemas |
| `influxdb` | influxdb:2.6 | **Time-series DB** — every measurement the Data Explorer charts |
| `nats` | nats | **Message broker** — carries events between pipeline elements |

Nothing to install separately: `docker compose up` pulls CouchDB, InfluxDB and NATS
as part of the stack. Credentials are baked into `docker-compose.yml`
(influx: org `sp`, bucket `sp`, token `sp-admin`; couch: `admin`/`admin`).

## 3. Walkthrough — adapter → pipeline → dashboard (~20 min)

### 3a. Adapter (Connect)

1. **Connect** → **New adapter** → search **Machine Data Simulator**.
2. Configure: **Wait Time** `1000` ms, **Sensor** `flowrate`.
   The flowrate scenario emits `sensorId, mass_flow (0–10), volume_flow (0–10),
   temperature (40–100 °C), density (40–50), sensor_fault_flags (bool)` and
   **deliberately goes into a defect mode after 30 s** — that fault is what you alarm on.
3. Next through the schema editor (it infers types; mark the timestamp field).
4. Name it `flowrate_demo` → **Start adapter**. It now appears under **Data Streams**.

### 3b. Pipeline (Pipeline Editor)

1. **Pipeline Editor**. First open shows a splash — "Start tour" runs the built-in
   interactive tutorial (water-tank example); skip it if you're following this.
2. Drag `flowrate_demo` from the left onto the canvas.
3. Drag **Numerical Filter** (or **Threshold Detection**) in, wire stream → processor,
   configure: field `temperature`, operator `>`, threshold `85`.
4. Drag **Dashboard Sink** in, wire processor → sink, give it a visualisation name.
5. **Save** → tick **Start pipeline immediately** → Save.
   The pipeline now shows as running under **Pipelines**.

### 3c. Dashboard

1. **Dashboard** → **New dashboard** → **Add visualisation**.
2. Pick the data source you named in the Dashboard Sink → choose widget
   (line chart for `temperature`, gauge, or table) → configure fields → save.
3. Watch it live. ~30 s in, the simulator's defect mode fires, temperature crosses
   85, events start flowing through the filter and spike on the chart.

### 3d. History (Data Explorer)

Add a **Data Lake** sink to the same pipeline (parallel to the Dashboard Sink) and
give it a measurement name. That writes into InfluxDB; **Data Explorer** then charts
it over any time range. Dashboard = live, Data Explorer = historical. Two different
sinks — a pipeline that only has a Dashboard Sink stores nothing.

## 4. Mapping to the motor demo

| Demo need | StreamPipes piece |
|---|---|
| Replay recorded motor/pump data | File adapter, or script → MQTT adapter |
| Broadband RMS threshold (L1) | Threshold Detection processor — no code |
| NDE vs pump channel comparison | Two streams + a join/merge processor |
| FFT / band energy / rotor-bar detection | **Custom Java processor** (SDK + Maven archetype) — not bundled |
| Health index, prognosis (L3–L5) | Custom processor / Python function |
| CMMS work order | Notification or REST sink |
| Live screens | Dashboard; history via Data Lake sink + Data Explorer |

## 5. Gotcha

The quick-start `curl` on the Apache download page points at raw GitHub ref `0.98.0`,
but the actual tag is `release/0.98.0` — the published one-liner 404s. The files in
this folder were fetched from the correct ref.

## 6. First-boot gotcha — empty adapter list (already handled)

**Symptom:** Connect → New adapter shows a blank "Select Adapter" list.

**Cause:** A fresh StreamPipes install registers its ~121 bundled elements
(32 adapters, 59 processors, 30 sinks) as *available* but not *installed*.
The first-run Setup wizard normally installs them, but this compose
auto-provisions the default admin and skips that step — so the list is empty
until they're installed once. The extensions container is healthy; nothing is
broken. Installed state is stored in CouchDB and persists across restarts.

**Fix (automatic):** `.devcontainer` runs `install-extensions.sh` on every
Codespace start. On the very first boot, give it ~2–3 min after the UI loads,
then reload — the adapters appear. Progress log: `cat /tmp/sp-install.log`.

**Fix (manual), e.g. after `docker compose down -v`:**
```bash
BASE=http://localhost:80 ./install-extensions.sh
```
The script is idempotent — it skips anything already installed.

## 7. White-labelling — Atosu branded image (option B)

A thin custom image (`branding/Dockerfile.ui`, `FROM apachestreampipes/ui:0.98.0`)
bakes the full Atosu identity into the UI — no npm build, builds in seconds:

- **Logos** — login, startup splash and top-bar (`assets/img/sp/logo*.png`)
- **Favicon** — browser tab + splash mark
- **Title** — `<title>` becomes "Atosu Engineering — AHCM" (no more "Apache StreamPipes")
- **Theme** — `branding/atosu-brand.css` overrides the StreamPipes green with the
  deck palette: navy `#03184A`, maroon `#9C2815`, teal `#3EC6CC`/`#0B7F84`.
  Injected via a `<link>` added to `index.html`, so it wins over the compiled green.

`docker-compose.override.yml` tells Compose to build this image as
`atosu/streampipes-ui:0.98.0` in place of the stock UI.

**Apply (in the Codespace terminal):**
```bash
git pull
docker compose up -d --build ui      # builds the branded image, restarts ui
```
Then hard-refresh the browser (Cmd/Ctrl+Shift+R).

**Change the logo/colours:** edit the files in `branding/` (keep the filenames;
`logo-navigation.png` must be a white version for the navy bar), then re-run the
`up -d --build ui` line. Tweak hex values in `atosu-brand.css`.

**Shareable:** the image is self-contained — no override or bind-mounts needed to
run it elsewhere; push `atosu/streampipes-ui:0.98.0` to a registry and reference it.

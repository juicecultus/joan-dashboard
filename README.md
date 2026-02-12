# Joan Dashboard

A custom dashboard for **Joan 13" e-ink displays** that shows weather, Google Calendar events, and Google Tasks — rendered as a PNG image and pushed via the [Visionect Software Suite (VSS)](https://docs.visionect.com/).

![Dashboard Preview](docs/preview.png)

## Features

- **Clock** — large, always-current time display
- **Month calendar** — compact mini calendar with today highlighted
- **Weather** — current conditions, feels-like temperature, sunrise/sunset, and 3-day forecast via [Open-Meteo](https://open-meteo.com/) (free, no API key)
- **Google Calendar** — today's schedule + full week ahead from all your calendars
- **Google Tasks** — to-do list with checkboxes, dynamically fills available space
- **Battery level** — live device battery percentage from VSS
- **Auto-refresh** — configurable loop interval (default: 60 seconds)
- **Preview mode** — render locally without pushing to the device
- **Runs on Raspberry Pi** — deploy as a systemd service alongside VSS for always-on operation

## How It Works

Joan devices are thin clients. They don't run apps — instead, they periodically poll a **Visionect Software Suite (VSS)** server for a pre-rendered image. This project:

1. Fetches weather, calendar events, and tasks from APIs
2. Renders a 1600×1200 grayscale PNG using Python Pillow
3. Pushes the image to VSS via its HTTP API
4. The Joan device picks it up on its next poll cycle

## Prerequisites

| Requirement | Notes |
|---|---|
| **Joan 13" device** | Any Joan device managed by VSS |
| **Visionect Software Suite** | Running on a Raspberry Pi, server, or VM ([install guide](https://docs.visionect.com/)) |
| **Python 3.9+** | With pip |
| **Google account** | For Calendar and Tasks integration |

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/juicecultus/joan-dashboard.git
cd joan-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
VSS_HOST=192.168.1.100       # IP of your VSS server
DEVICE_UUID=your-uuid-here   # Find in VSS web UI → Devices
WEATHER_LAT=51.509            # Your latitude
WEATHER_LON=-0.118            # Your longitude
WEATHER_LOCATION=London       # Display name
```

**Finding your Device UUID:** Open the VSS web UI at `http://<VSS_HOST>:8081`, go to Devices, and copy the UUID of your Joan device.

### 3. Set up Google Calendar & Tasks

Create OAuth2 credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Navigate to **APIs & Services → Library**
4. Enable **Google Calendar API** and **Google Tasks API**
5. Go to **APIs & Services → Credentials**
6. Click **Create Credentials → OAuth client ID**
7. Application type: **Desktop app**
8. Download the JSON file and save it as `credentials.json` in this directory

Then run the authentication helper:

```bash
python joan_google_auth.py
```

This opens a browser window. Log in with the Google account whose calendar and tasks you want to display. The token is saved to `token.json` (git-ignored).

### 4. Preview

```bash
python joan_dashboard.py --preview
```

This renders the dashboard and saves it as `joan_preview.png` without pushing to the device. Great for testing layout changes.

### 5. Push to Joan

```bash
python joan_dashboard.py
```

Single render + push to the device.

### 6. Auto-refresh

```bash
python joan_dashboard.py --loop 60
```

Renders and pushes every 60 seconds. The image on VSS is always fresh when the device next polls.

**Battery note:** The `--loop` interval controls how often your *server* pushes a new image. The Joan device's own poll interval (configured in VSS) determines battery drain. A 5-minute device poll interval gives ~4-6 months battery life on the 10,000mAh Joan 13".

## Layout

```
┌──────────────┬─────────────────────┬──────────────────┐
│              │  Thursday, 12 Feb   │       8°         │
│    13:37     │  ┌──────────────┐   │   Light rain     │
│              │  │ Month  Cal   │   │   Feels 6°       │
│              │  │  grid  here  │   │  Rise/Set times  │
│              │  └──────────────┘   │  3-day forecast  │
├──────────────┴──────────┬──────────┴──────────────────┤
│         To Do           │          Schedule           │
│  □ Task 1               │  Today                     │
│  □ Task 2               │    No events / event list  │
│  □ Task 3               │  This Week                 │
│  □ ...                  │    Fri 13 - Event...       │
│  (fills remaining       │    Sat 14 - Event...       │
│   space dynamically)    │    (tomorrow onwards)      │
└─────────────────────────┴────────────────────────────┘
```

## Running as a Service

### Recommended: Raspberry Pi with systemd

The best setup is running the dashboard loop on the **same Raspberry Pi** that hosts your VSS server. This way the display keeps updating even when your laptop is off, and the push happens over localhost with zero latency.

#### 1. Set up the project on the Pi

SSH into your Pi and clone the repo:

```bash
ssh youruser@192.168.x.x
git clone https://github.com/juicecultus/joan-dashboard.git
cd joan-dashboard
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

> **Note:** On some Pi OS versions you may need `sudo apt install python3-venv python3-dev fonts-dejavu` first.

#### 2. Copy your Google credentials

From your local machine (where you ran `joan_google_auth.py`):

```bash
scp credentials.json token.json youruser@192.168.x.x:~/joan-dashboard/
```

#### 3. Configure

```bash
cp .env.example .env
nano .env
```

Since VSS is on the same Pi, set the host to localhost:

```env
VSS_HOST=127.0.0.1
VSS_PORT=8081
DEVICE_UUID=your-uuid-here
WEATHER_LAT=51.509
WEATHER_LON=-0.118
WEATHER_LOCATION=London
```

#### 4. Test it

```bash
.venv/bin/python joan_dashboard.py --preview   # render locally
.venv/bin/python joan_dashboard.py              # render + push once
```

#### 5. Create the systemd service

```bash
sudo tee /etc/systemd/system/joan-dashboard.service > /dev/null << 'EOF'
[Unit]
Description=Joan E-Ink Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/joan-dashboard
ExecStart=/home/youruser/joan-dashboard/.venv/bin/python joan_dashboard.py --loop 60
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
```

Replace `youruser` with your Pi username.

#### 6. Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable joan-dashboard
sudo systemctl start joan-dashboard
```

#### Managing the service

```bash
sudo systemctl status joan-dashboard    # check status
sudo systemctl restart joan-dashboard   # restart after changes
sudo systemctl stop joan-dashboard      # stop
journalctl -u joan-dashboard -f         # live logs
```

#### Updating the dashboard

When you push changes to GitHub:

```bash
cd ~/joan-dashboard
git pull
sudo systemctl restart joan-dashboard
```

### Alternative: macOS (launchd)

If you prefer running the loop on your Mac instead of the Pi:

Create `~/Library/LaunchAgents/com.joan.dashboard.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.joan.dashboard</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/joan-dashboard/.venv/bin/python</string>
        <string>/path/to/joan-dashboard/joan_dashboard.py</string>
        <string>--loop</string>
        <string>60</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>/path/to/joan-dashboard</string>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.joan.dashboard.plist
```

> **Note:** The dashboard reads `.env` from the project directory automatically, so environment variables don't need to be duplicated in the plist.

## Customisation

### Change the layout

The entire dashboard is rendered in `render_dashboard()` in `joan_dashboard.py`. It uses a grid system with constants at the top:

```python
PAD = 40          # outer margin
GAP = 20          # gap between sections
HEADER_H = 420    # header row height
COL_DIV = 800     # column divider x position
LINE_H = 38       # standard line height
```

### Change fonts

The `get_font()` function searches for system fonts. It tries Helvetica (macOS), then DejaVu Sans and Liberation Sans (Linux). Add your preferred font paths to the `candidates` lists.

### Change weather location

Set `WEATHER_LAT`, `WEATHER_LON`, and `WEATHER_LOCATION` in your `.env` file. Coordinates can be found at [latlong.net](https://www.latlong.net/).

## Troubleshooting

| Problem | Solution |
|---|---|
| "Weather unavailable" | Check your internet connection. Open-Meteo is free and has no API key, so it should just work. |
| No calendar events | Run `python joan_google_auth.py` to re-authenticate. Check that Calendar API is enabled in Google Cloud Console. |
| Image not appearing on Joan | Verify `VSS_HOST`, `DEVICE_UUID` in `.env`. Check VSS web UI at `http://<VSS_HOST>:8081`. |
| Fonts look wrong | Install `fonts-dejavu` on Linux (`sudo apt install fonts-dejavu`). On macOS, Helvetica is used by default. |
| Token expired | Delete `token.json` and re-run `python joan_google_auth.py`. |
| Service won't start on Pi | Check logs with `journalctl -u joan-dashboard -e`. Ensure `.venv` exists and deps are installed. |
| Google auth on headless Pi | Run `joan_google_auth.py` on your laptop first, then `scp` the `token.json` and `credentials.json` to the Pi. |

## Tech Stack

- **Python 3** + **Pillow** for image rendering
- **Open-Meteo API** for weather (free, no key required)
- **Google Calendar API v3** + **Google Tasks API v1** via OAuth2
- **Visionect Software Suite** HTTP API for device communication

## License

MIT

## Credits

Built by [Justinian](https://github.com/juicecultus) for the Joan e-ink display community.

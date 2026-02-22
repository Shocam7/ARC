# ARC — Augmented Reality Conferencing

> A modern video meeting web app with live world-background sharing.

---

## Features

- **Join as a Guest** — Create or join meeting rooms with a short code (like Google Meet)
- **Share a World** — Turn your camera into a live ambient background for all participants
- **WebRTC Mesh** — Peer-to-peer video/audio, no media relay costs
- **Free forever** — Runs entirely on Google Cloud free-tier services

---

## Tech Stack

| Layer | Technology | Cost |
|---|---|---|
| Server | Node.js + Express + Socket.io | Free |
| WebRTC Signaling | Socket.io (WebSocket) | Free |
| STUN Servers | Google Public STUN | Free forever |
| Hosting | Google Cloud Run | Free tier (2M req/mo) |
| Container Registry | Google Artifact Registry | Free tier (500MB) |

> **No paid services required.** Google Cloud Run has a permanent free tier of 2 million requests/month and 360,000 GB-seconds of compute. Google's public STUN servers (`stun.l.google.com`) are free forever.

---

## Local Development

```bash
# 1. Install dependencies
npm install

# 2. Start dev server
npm run dev

# 3. Open http://localhost:8080
```

---

## Deploy to Google Cloud Run (Free)

### Prerequisites
- Google Cloud account (free trial or free tier)
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`) installed
- Docker installed (for local build) or use Cloud Build

---

### Step 1 — Set up your project

```bash
# Login to Google Cloud
gcloud auth login

# Create a new project (or use existing)
gcloud projects create arc-meeting-app --name="ARC Meeting"
gcloud config set project arc-meeting-app

# Enable required APIs (free)
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

---

### Step 2 — Build and push with Cloud Build (free 120 min/day)

```bash
# Set your project ID
export PROJECT_ID=$(gcloud config get-value project)

# Build and push using Cloud Build (no local Docker needed)
gcloud builds submit --tag gcr.io/$PROJECT_ID/arc-meeting:latest .
```

**OR** build locally with Docker:

```bash
export PROJECT_ID=$(gcloud config get-value project)

# Configure Docker auth for GCR
gcloud auth configure-docker

# Build locally
docker build -t gcr.io/$PROJECT_ID/arc-meeting:latest .

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/arc-meeting:latest
```

---

### Step 3 — Deploy to Cloud Run

```bash
gcloud run deploy arc-meeting \
  --image gcr.io/$PROJECT_ID/arc-meeting:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 3600
```

> `--timeout 3600` is important — WebSocket connections need long timeouts for live meetings.

After deployment, Cloud Run will give you a URL like:
```
https://arc-meeting-xxxxxxxxxx-uc.a.run.app
```

---

### Step 4 — (Optional) Custom Domain

```bash
# Map a custom domain (free SSL included)
gcloud run domain-mappings create \
  --service arc-meeting \
  --domain yourdomain.com \
  --region us-central1
```

---

## Continuous Deployment with Cloud Build

Create `cloudbuild.yaml` in the project root:

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/arc-meeting:$COMMIT_SHA', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/arc-meeting:$COMMIT_SHA']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - gcloud
      - run
      - deploy
      - arc-meeting
      - --image=gcr.io/$PROJECT_ID/arc-meeting:$COMMIT_SHA
      - --region=us-central1
      - --platform=managed
```

Connect your GitHub repo in the Cloud Build console for auto-deploy on every push.

---

## Architecture

```
Browser A (Guest)          Browser B (World Sharer)
     |                              |
     |──── Socket.io signal ────────|
     |              |               |
     |         ARC Server           |
     |        (Cloud Run)           |
     |              |               |
     |──────────────────────────────|
     |                              |
     |←──── WebRTC P2P stream ─────→|
     
     World video renders as full-screen
     background in all guest browsers
```

### How "Share a World" works

1. **World sharer** opens `world.html`, camera starts streaming
2. They join the room via Socket.io with `role: 'world'`
3. For each guest in the room, the world sharer creates a **WebRTC peer connection** and sends their camera stream
4. Each guest's browser receives the stream and renders it as a `<video>` element behind all participant tiles
5. CSS `filter: brightness(0.45) blur(1px)` creates the ambient background effect

---

## Free Tier Limits (Google Cloud)

| Service | Free Tier | Notes |
|---|---|---|
| Cloud Run | 2M requests/month, 360K GB-sec | Resets monthly |
| Cloud Build | 120 build-minutes/day | Enough for dozens of deploys |
| Container Registry | 500MB storage | ~10 images |
| Networking egress | 1GB/month | WebRTC is P2P (no server egress) |

> Since ARC uses WebRTC for all media (P2P), **the server only handles signaling text messages**, which are tiny. You'll stay well within free limits for typical usage.

---

## Security Notes

- All WebRTC streams are **end-to-end encrypted** (DTLS-SRTP)
- Room IDs are randomly generated 9-character codes
- Rooms auto-delete when empty
- No data is stored server-side — everything is in memory

---

## Project Structure

```
arc/
├── server.js              # Express + Socket.io signaling server
├── package.json
├── Dockerfile
├── cloudrun-service.yaml  # Optional: declarative Cloud Run config
└── public/
    ├── index.html         # Landing page
    ├── meeting.html       # Meeting room (guest view)
    └── world.html         # World broadcaster view
```

---

## Troubleshooting

**WebSocket disconnects on Cloud Run?**
Make sure `--timeout 3600` is set. Cloud Run defaults to 300s which kills long-lived WebSocket connections.

**Can't connect to room?**
Cloud Run scales to zero when idle. The first request after idle takes ~2-3 seconds (cold start). This is normal.

**World video not showing for guests?**
Check browser console for WebRTC errors. Both peers must be on HTTPS (Cloud Run provides this automatically). Local development also works since `localhost` is treated as secure.

**STUN failing?**
The app uses Google's public STUN servers. If behind a restrictive firewall, you may need to add a TURN server. [Metered.ca](https://www.metered.ca/tools/openrelay/) offers a free TURN relay for development.

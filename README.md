# Duologue AI

Turn any article, PDF, URL, or topic into a downloadable podcast episode where **two AI hosts** have a natural conversation about it — generated, voiced, stitched, and stored, entirely on free infrastructure.

**Live demo:** https://duologue-ai.streamlit.app

---

## What it does

Give Duologue AI some source material and a few options; it returns a finished MP3 of two named AI hosts discussing it like a real show, saved to a browsable library.

**Inputs:** pasted text · PDF upload · article URL · topic-only prompt
**Options:** tone (Casual / Academic / Comedic / Debate) · length (5 / 15 / 30 min) · host pair (Two Friends · Expert + Novice · Skeptic + Believer)
**Output:** a single downloadable MP3 with two distinct voices, an episode title, a transcript, and a saved library entry.

---

## How it works

A linear pipeline; each stage is one clean transformation:

```
Source (text / PDF / URL / topic)
   │        └─ topic only → llama-3.1-8b writes a short research brief
   ▼
clean text  ──►  Groq · llama-3.3-70b  →  JSON { title, script[] }   (two-host dialogue)
   ▼
TTS fallback chain  ──►  Edge TTS → gTTS   (whole episode, first provider that succeeds)
   ▼
pydub + ffmpeg  ──►  one MP3, 300 ms gaps between turns
   ▼
Supabase  ──►  upload MP3 to Storage + insert metadata row
   ▼
play · download · saved to "My Episodes"
```

---

## Tech stack (and why)

| Layer | Tool | Why |
|-------|------|-----|
| UI + backend | **Streamlit** | Pure-Python web app; fastest way for one person to ship an AI demo. |
| Hosting | **Streamlit Community Cloud** | Free, deploys from GitHub, auto-redeploys on push. *(Replaced Hugging Face Spaces after HF dropped its free compute tier mid-build.)* |
| LLM | **Groq** — `llama-3.3-70b-versatile` + `llama-3.1-8b-instant` | Free, no card, fast. 70B writes the dialogue; the cheaper 8B writes topic research briefs. |
| Text-to-speech | **Edge TTS → gTTS** (fallback chain) | Free. Edge gives distinct neural voices; gTTS is a resilient fallback when Edge is blocked. |
| Audio | **pydub + ffmpeg** | Concatenate per-turn clips with silence gaps, export MP3. |
| Storage + database | **Supabase** (Storage + Postgres) | Free, no card, one service for both the MP3s and the metadata. *(Replaced Cloudflare R2, which requires a payment method.)* |
| Secrets | **`st.secrets`** | One code path for local and cloud; nothing in git. |
| Keep-alive | **GitHub Actions** (scheduled cron) | Pings the database daily so the free Supabase project never hits its 7-day inactivity pause. |
| Deploy | **GitHub → Streamlit Cloud** | Push to deploy. |

---

## Project structure

The app is split by responsibility. Only `app.py` touches Streamlit, secrets, and logging; every other module is pure logic that takes inputs and returns outputs (or raises), which keeps the core framework-agnostic and testable.

```
duologue-ai/
├── app.py            # Streamlit UI + orchestration (the only file that imports streamlit)
├── config.py         # tones, lengths, host presets (names + personas), constants
├── ingestion.py      # PDF (pypdf) and URL (trafilatura) -> clean text
├── script.py         # Groq: topic research brief + script/title generation (+ custom exceptions)
├── tts.py            # provider fallback orchestrator (first success wins)
├── tts_edge.py       # TTS provider - Edge TTS, distinct neural voices
├── tts_gtts.py       # TTS provider - gTTS fallback, accent-differentiated
├── audio.py          # pydub stitching -> one MP3 + duration
├── db.py             # Supabase: upload MP3, save/list episode metadata, public URLs
├── .streamlit/
│   └── config.toml   # theme
├── requirements.txt  # Python dependencies
├── packages.txt      # system packages (ffmpeg) for the cloud build
└── .github/workflows/keepalive.yml   # Supabase keep-alive cron
```

---

## Running locally

**Prerequisites:** Python 3.10+, git, and **ffmpeg** on your machine
- Windows: `winget install Gyan.FFmpeg` (then open a new terminal)
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

```bash
git clone https://github.com/YOUR_USERNAME/duologue-ai.git
cd duologue-ai

python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows
# source .venv/bin/activate         # macOS/Linux

pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` (git-ignored):

```toml
GROQ_API_KEY = "gsk_..."            # console.groq.com
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "eyJ..."             # the service_role key (server-side only)
```

Then:

```bash
streamlit run app.py
```

---

## Deployment notes

- Auto-deploys on every push to `main` via Streamlit Community Cloud.
- `packages.txt` (containing `ffmpeg`) installs the system binary at build time — the Debian `ffmpeg` package also provides `ffprobe`, which pydub needs.
- Secrets (`GROQ_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`) live in the Streamlit Cloud app settings, not the repo.
- The Supabase table (`episodes`) and a public Storage bucket (`episodes`) must exist; a keep-alive GitHub Action prevents the free project from pausing.

---

## Known limitations (by design, and honest)

- **5-minute episodes are the reliable length.** The free Groq tier's tokens-per-minute budget is tight for the 70B model, so 15/30-min scripts can truncate. Long-form generation (producing the script in sections) is future work.
- **In production, voices come from the gTTS fallback.** Microsoft blocks Edge TTS from datacenter IPs, so the deployed app uses gTTS (accent-differentiated, one voice) rather than Edge's distinct neural voices — which work locally. The fallback chain keeps the app functional and tells the listener when backup voices are used.
- **No authentication → the library is global.** Every visitor sees every episode. Per-user libraries need auth.
- **Rate limiting is per session.** It blocks 5 generations/hour per browser session (resets on refresh); true per-IP limiting would need a shared store or a gateway in front of the app.
- **The free Supabase project pauses after 7 days idle**; the GitHub Actions keep-alive mitigates this, but a repo with no commits for 60+ days would eventually let scheduled workflows disable.
- **Streamlit's theming is limited**, so the styling takes the robust 80% (theme + a little CSS) rather than pixel-perfect control.

---

## Roadmap

- [ ] Authentication + per-user libraries
- [ ] A third TTS provider for distinct voices in production
- [ ] Cover art (a generated title card, or an image API)
- [ ] Long-form (15/30-min) episodes via chunked generation
- [ ] Stricter structured output via Groq `json_schema`

---

## More

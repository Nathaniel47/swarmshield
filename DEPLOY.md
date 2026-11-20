# Deploying the SwarmShield demo

The demo is the Streamlit dashboard in `dashboard/app.py`. It runs the offline scripted agent, so it needs **no API key and no secrets**, visitors need **no sign-up**, and every run takes milliseconds. Verified locally: the locked-down Docker image reaches the full page in about 5 seconds from a cold start.

## Recommended: Streamlit Community Cloud (free)

Why: the app is Streamlit, so it deploys straight from the GitHub repo with no Docker, and the free tier is enough for a static, key-free demo. The first visit after an idle period takes a few seconds longer while the app wakes up.

Only step 1 needs your own login.

1. Go to https://share.streamlit.io and sign in with the GitHub account that owns `Nathaniel47/swarmshield` (**needs your login**; authorise access to the public repo if asked).
2. Click **Create app**, then **Deploy a public app from GitHub**, and set:
   - Repository: `Nathaniel47/swarmshield`
   - Branch: `main`
   - Main file path: `dashboard/app.py`
   - App URL: pick a name, for example `swarmshield`
3. Open **Advanced settings**, choose **Python 3.11**, and leave **Secrets** empty (the demo uses none). Dependencies come from `requirements.txt`, which contains only the four libraries the demo needs.
4. Click **Deploy**. The first build takes a couple of minutes.
5. Put the resulting URL in the README (`Demo:` line) and in `PORTFOLIO.md`.

Redeploys happen automatically on every push to `main`.

## Alternative: any Docker host (Hugging Face Spaces, Render, Fly.io)

The `Dockerfile` runs the same app as a non-root user, listening on `$PORT` (default 8501).

```bash
docker build -t swarmshield .
docker run --rm -p 8501:8501 --read-only --tmpfs /tmp --cap-drop ALL \
  --security-opt no-new-privileges:true --memory 2g swarmshield
```

Then open http://localhost:8501. The same image works on Render (new Web Service from the repo, runtime Docker) and on a Hugging Face Space with the Docker SDK (add `app_port: 8501` to the Space's README header).

## API keys

The demo never calls a model, so deploy it without secrets. The real Groq and Gemini backends exist for offline experiments only (`pip install -r requirements-llm.txt`, keys in a git-ignored `.env` as `SWARMSHIELD_GROQ_API_KEY` and `SWARMSHIELD_GEMINI_API_KEY`). If a live-model mode is ever added to the public app, the keys must go in the host's secrets store (Streamlit: **Secrets**, read with `st.secrets`) and the mode needs a per-visitor rate limit and a daily call cap, because the free tiers are small.

## Checking a deployment

- The page shows "Agents ever infected 6 of 6" and a graph within about 10 seconds.
- Clicking **Worm on a mesh, all defences** turns the graph mostly green and the final report to OK.
- The **Results** tab shows three charts and the results table.

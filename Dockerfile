FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=8501 \
    SWARMSHIELD_STATE_DIR=/tmp/swarmshield/state \
    SWARMSHIELD_CACHE_DIR=/tmp/swarmshield/cache \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN useradd --create-home --uid 1000 swarm
COPY --chown=swarm:swarm . .
USER swarm
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD python -c "import os,urllib.request as u; u.urlopen('http://localhost:'+os.environ['PORT']+'/_stcore/health')"
CMD ["sh", "-c", "streamlit run dashboard/app.py --server.address=0.0.0.0 --server.port=${PORT} --server.headless=true"]

# QRL Web Wallet container
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Runtime libs
RUN apt-get update \
 && apt-get install -y --no-install-recommends libssl-dev libgmp-dev \
 && rm -rf /var/lib/apt/lists/*

# Install dependencies with pinned hashes
COPY requirements.lock requirements.lock
RUN python -m pip install --upgrade pip \
 && python -m pip install --require-hashes -r requirements.lock

# Project files
COPY . .

ENV PORT=5001
EXPOSE 5001

# Use Gunicorn for production serving; expand $PORT at runtime
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import os,sys,urllib.request; url=f'http://127.0.0.1:{os.environ.get('PORT','5001')}/healthz';\ntry:\n r=urllib.request.urlopen(url, timeout=3);\n sys.exit(0 if getattr(r,'status',200)==200 else 1)\nexcept Exception:\n sys.exit(1)"
CMD gunicorn -w 2 -k gthread -b 0.0.0.0:${PORT:-5001} qrl.web_wallet:app

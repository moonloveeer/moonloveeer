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
CMD gunicorn -w 2 -k gthread -b 0.0.0.0:${PORT:-5001} qrl.web_wallet:app

# ===============================
# Dockerfile for Flask + Ollama
# ===============================

FROM ubuntu:22.04

# ---- System deps ----
RUN apt-get update && apt-get install -y \
    python3 python3-pip curl git && \
    apt-get clean

# ---- Install Ollama ----
RUN curl -fsSL https://ollama.com/install.sh | sh

# ---- Copy project ----
WORKDIR /app
COPY . /app

# ---- Python deps ----
RUN pip3 install --no-cache-dir -r requirements.txt

# ---- Expose Flask & Ollama ports ----
EXPOSE 5000 11434

# ---- Start Ollama + Flask ----
CMD ollama serve & gunicorn app:app --bind 0.0.0.0:5000

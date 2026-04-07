FROM python:3.12-slim

WORKDIR /app

# Install Stockfish from apt
RUN apt-get update && \
    apt-get install -y --no-install-recommends stockfish && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Stockfish path for the app
ENV STOCKFISH_PATH=/usr/games/stockfish
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

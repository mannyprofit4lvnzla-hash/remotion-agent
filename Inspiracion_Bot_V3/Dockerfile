FROM python:3.11-slim-bookworm

# Install required system binaries for MoviePy (FFmpeg & ImageMagick for TextClips)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Fix ImageMagick security policy to allow reading/writing text via MoviePy
RUN sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/g' /etc/ImageMagick-6/policy.xml || true
RUN sed -i 's/rights="none" pattern="LABEL"/rights="read|write" pattern="LABEL"/g' /etc/ImageMagick-6/policy.xml || true
RUN sed -i 's/rights="none" pattern="@*"/rights="read|write" pattern="@*"/g' /etc/ImageMagick-6/policy.xml || true

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]

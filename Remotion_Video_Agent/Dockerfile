
FROM python:3.11-slim-bookworm

# 1. Install System Dependencies
# We need curl for Node setup, ffmpeg for audio processing, and libraries for Chrome/Remotion
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    unzip \
    ffmpeg \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libxss1 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# 3. Install Chromium (Stable) for Remotion
# Remotion will look for a browser. Chromium from apt is usually easiest on Debian.
RUN apt-get update && apt-get install -y chromium \
    && rm -rf /var/lib/apt/lists/*

# Set env var so Remotion knows where Chromium is (optional but helpful)
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true

# 4. Set Up Application Directory
WORKDIR /app

# 5. Copy and Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy and Install Node Dependencies (Remotion)
# We assume the remotion project is in a subdirectory 'remotion'
COPY remotion/package.json remotion/package-lock.json* ./remotion/
WORKDIR /app/remotion
RUN npm install
# Go back to root
WORKDIR /app

# 7. Copy Application Code
COPY . .

# 8. Start the Bot
CMD ["python", "bot.py"]

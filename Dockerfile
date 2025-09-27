FROM python:3.9-slim

# Install dependencies and download wkhtmltopdf manually
RUN apt-get update && apt-get install -y \
    wget \
    xvfb \
    fontconfig \
    libjpeg62-turbo \
    libxrender1 \
    libfontconfig1 \
    libx11-6 \
    libxext6 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# Download and install wkhtmltopdf directly
RUN wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bullseye_amd64.deb \
    && dpkg -i wkhtmltox_0.12.6.1-3.bullseye_amd64.deb || true \
    && apt-get update && apt-get -f install -y \
    && rm wkhtmltox_0.12.6.1-3.bullseye_amd64.deb

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]

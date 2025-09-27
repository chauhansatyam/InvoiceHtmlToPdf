#!/bin/bash

# Install system dependencies
apt-get update
apt-get install -y wkhtmltopdf || echo "wkhtmltopdf install failed, will use WeasyPrint"

# Install Python dependencies
pip install -r requirements.txt

echo "Build completed successfully"

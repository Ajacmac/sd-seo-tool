FROM python:3.12.3-slim

WORKDIR /app

RUN apt-get update && apt-get install -y lsof

# Handle dependencies first so the layers are cached
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Add src to Python path
ENV PYTHONPATH=/app/src

# Expose the port the app runs on
EXPOSE 8000

# Install necessary packages and Litestream
RUN apt-get install -y curl && \
    curl -L https://github.com/benbjohnson/litestream/releases/download/v0.3.13/litestream-v0.3.13-linux-amd64.tar.gz > /tmp/litestream.tar.gz && \
    tar -C /usr/local/bin -xzf /tmp/litestream.tar.gz && \
    rm /tmp/litestream.tar.gz && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy Litestream configuration
COPY litestream.yml /etc/litestream.yml

# Use a script to run Litestream and your app
COPY run.sh /run.sh
RUN chmod +x /run.sh

RUN chmod +x /app/misc_scripts/disk_analysis.py

# Regular execution
CMD ["/run.sh"]

# Running optional disk check script
# CMD ["/run.sh", "--disk-check"]

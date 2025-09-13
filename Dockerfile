ARG BUILDPLATFORM="linux/amd64"

FROM ghcr.io/orchestra-labs/symphony:latest AS symphony
FROM --platform=${BUILDPLATFORM} python:3-bookworm
LABEL org.opencontainers.image.description="Symphony blockchain price feeder"
LABEL org.opencontainers.image.source=https://github.com/cmancrypto/symphony-oracle-voter

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y curl jq && rm -rf /var/lib/apt/lists/*

WORKDIR /symphony
COPY --from=symphony /bin/symphonyd /usr/local/bin

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Copy and set up the entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh && \
    sed -i 's/\r$//' /usr/local/bin/entrypoint.sh

# Set default environment variables (these can be overridden)
ENV PYTHON_ENV=production
ENV LOG_LEVEL=INFO
ENV DEBUG=false
ENV SYMPHONYD_PATH=symphonyd
ENV KEY_BACKEND=test
ENV CHAIN_ID=symphony-1

# Create data directory for potential volume mounts
RUN mkdir -p /symphony/data

EXPOSE 19000

# Use the new entrypoint script
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
# ─────────────────────────────────────────────────────────────────────────────
# Cartographer Nginx - TLS Termination Proxy
# ─────────────────────────────────────────────────────────────────────────────

FROM nginx:1.25-alpine

# Install certbot for Let's Encrypt certificate management
RUN apk add --no-cache \
    certbot \
    certbot-nginx \
    openssl

# Create directories for certificates and ACME challenges
RUN mkdir -p /etc/nginx/ssl /var/www/certbot

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Generate self-signed certificate for initial startup
# This allows the container to start before real certificates are obtained
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/privkey.pem \
    -out /etc/nginx/ssl/fullchain.pem \
    -subj "/CN=localhost" \
    && chmod 600 /etc/nginx/ssl/privkey.pem

# Expose HTTP and HTTPS ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/healthz || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

#!/bin/bash
# ==============================================================================
# StaffSync 360 - Automated SSL/TLS Certificate Provisioning Script
# ==============================================================================
set -e

SSL_DIR="./deploy/ssl"
DOMAIN="${1:-localhost}"

mkdir -p "${SSL_DIR}"

echo "[+] Initializing SSL/TLS Certificates for domain: ${DOMAIN}..."

if [ -f "${SSL_DIR}/cert.pem" ] && [ -f "${SSL_DIR}/key.pem" ]; then
    echo "[!] Existing certificates found at ${SSL_DIR}. Skipping generation."
    exit 0
fi

echo "[+] Generating 4096-bit RSA Private Key and Self-Signed Certificate..."
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
    -keyout "${SSL_DIR}/key.pem" \
    -out "${SSL_DIR}/cert.pem" \
    -subj "/C=IN/ST=Karnataka/L=Bangalore/O=StaffSync Enterprise/OU=Security/CN=${DOMAIN}" \
    -addext "subjectAltName=DNS:${DOMAIN},DNS:localhost,IP:127.0.0.1"

echo "[+] Generating 2048-bit Diffie-Hellman Parameter for Forward Secrecy..."
openssl dhparam -out "${SSL_DIR}/dhparam.pem" 2048

chmod 600 "${SSL_DIR}/key.pem"
chmod 644 "${SSL_DIR}/cert.pem"

echo "[✓] SSL/TLS initialization complete! Certificates saved to ${SSL_DIR}/"

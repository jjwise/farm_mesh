#!/usr/bin/env sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <mqtt-dns-name> <dashboard-dns-name>" >&2
  exit 2
fi

MQTT_DNS_NAME=$1
DASHBOARD_DNS_NAME=$2
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DEPLOY_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
SECRETS_DIR="$DEPLOY_DIR/secrets"
CERTS_DIR="$DEPLOY_DIR/mosquitto/certs"
CA_KEY="$SECRETS_DIR/mqtt_ca.key"
LEGACY_CA_KEY="$CERTS_DIR/ca.key"
CERT_DNS_FILE="$DEPLOY_DIR/generated/mqtt_dns_name"

command -v openssl >/dev/null 2>&1 || {
  echo "openssl is required" >&2
  exit 1
}
command -v docker >/dev/null 2>&1 || {
  echo "docker is required" >&2
  exit 1
}

umask 077
mkdir -p "$SECRETS_DIR" "$CERTS_DIR" "$DEPLOY_DIR/generated"

create_secret() {
  target=$1
  if [ ! -s "$target" ]; then
    openssl rand -base64 36 | tr -d '\n' > "$target"
    printf '\n' >> "$target"
  fi
}

create_secret "$SECRETS_DIR/postgres_password.txt"
create_secret "$SECRETS_DIR/mqtt_gateway_password.txt"
create_secret "$SECRETS_DIR/mqtt_backend_password.txt"
create_secret "$SECRETS_DIR/api_token.txt"
create_secret "$SECRETS_DIR/admin_token.txt"
create_secret "$SECRETS_DIR/web_password.txt"

if [ -s "$LEGACY_CA_KEY" ]; then
  if [ -s "$CA_KEY" ]; then
    echo "Both legacy and protected CA private keys exist; resolve this manually." >&2
    exit 1
  fi
  mv "$LEGACY_CA_KEY" "$CA_KEY"
fi

if [ ! -s "$CA_KEY" ] && [ ! -s "$CERTS_DIR/ca.crt" ]; then
  openssl genrsa -out "$CA_KEY" 4096
  openssl req -x509 -new -sha256 -days 3650 \
    -key "$CA_KEY" \
    -out "$CERTS_DIR/ca.crt" \
    -subj "/CN=Irrigation Tracker Private CA"
elif [ ! -s "$CA_KEY" ] || [ ! -s "$CERTS_DIR/ca.crt" ]; then
  echo "Incomplete MQTT CA state; restore both mqtt_ca.key and ca.crt." >&2
  exit 1
fi

REISSUE_SERVER_CERT=0
if [ ! -s "$CERTS_DIR/server.key" ] || [ ! -s "$CERTS_DIR/server.crt" ]; then
  REISSUE_SERVER_CERT=1
elif [ ! -s "$CERT_DNS_FILE" ] || [ "$(cat "$CERT_DNS_FILE")" != "$MQTT_DNS_NAME" ]; then
  REISSUE_SERVER_CERT=1
elif ! openssl verify -CAfile "$CERTS_DIR/ca.crt" "$CERTS_DIR/server.crt" >/dev/null 2>&1; then
  REISSUE_SERVER_CERT=1
elif ! openssl x509 -checkend 2592000 -noout -in "$CERTS_DIR/server.crt" >/dev/null 2>&1; then
  REISSUE_SERVER_CERT=1
fi

if [ "$REISSUE_SERVER_CERT" -eq 1 ]; then
  openssl genrsa -out "$CERTS_DIR/server.key" 2048
  openssl req -new -sha256 \
    -key "$CERTS_DIR/server.key" \
    -out "$CERTS_DIR/server.csr" \
    -subj "/CN=$MQTT_DNS_NAME"
  printf 'subjectAltName=DNS:%s\nextendedKeyUsage=serverAuth\n' "$MQTT_DNS_NAME" \
    > "$CERTS_DIR/server.ext"
  openssl x509 -req -sha256 -days 825 \
    -in "$CERTS_DIR/server.csr" \
    -CA "$CERTS_DIR/ca.crt" \
    -CAkey "$CA_KEY" \
    -CAcreateserial \
    -extfile "$CERTS_DIR/server.ext" \
    -out "$CERTS_DIR/server.crt"
  printf '%s\n' "$MQTT_DNS_NAME" > "$CERT_DNS_FILE"
fi

GATEWAY_PASSWORD=$(tr -d '\r\n' < "$SECRETS_DIR/mqtt_gateway_password.txt")
BACKEND_PASSWORD=$(tr -d '\r\n' < "$SECRETS_DIR/mqtt_backend_password.txt")
PASSWORD_FILE="$DEPLOY_DIR/mosquitto/passwords"

docker run --rm \
  -v "$DEPLOY_DIR/mosquitto:/mosquitto/config" \
  --entrypoint mosquitto_passwd \
  eclipse-mosquitto:2.0.22-openssl \
  -b -c /mosquitto/config/passwords irrigation-gateway "$GATEWAY_PASSWORD"
docker run --rm \
  -v "$DEPLOY_DIR/mosquitto:/mosquitto/config" \
  --entrypoint mosquitto_passwd \
  eclipse-mosquitto:2.0.22-openssl \
  -b /mosquitto/config/passwords irrigation-backend "$BACKEND_PASSWORD"
chmod 600 "$PASSWORD_FILE"

WEB_PASSWORD=$(tr -d '\r\n' < "$SECRETS_DIR/web_password.txt")
WEB_HASH=$(docker run --rm caddy:2.10-alpine caddy hash-password --plaintext "$WEB_PASSWORD")
{
  printf 'IRRIGATION_SITE_ADDRESS=%s\n' "$DASHBOARD_DNS_NAME"
  printf 'IRRIGATION_WEB_USERNAME=irrigation\n'
  printf "IRRIGATION_WEB_PASSWORD_HASH='%s'\n" "$WEB_HASH"
} > "$DEPLOY_DIR/.env"

echo "Bootstrap complete."
echo "Dashboard password: $SECRETS_DIR/web_password.txt"
echo "Gateway MQTT password: $SECRETS_DIR/mqtt_gateway_password.txt"
echo "Next: render the firmware header, then run 'docker compose up -d --build'."

# Self-hosted deployment

The stack deliberately keeps only three host ports open:

- `8883/tcp`: Mosquitto MQTT over verified TLS.
- `80/tcp` and `443/tcp`: Caddy, which redirects to HTTPS and protects the
  dashboard/API with Basic Auth.

PostgreSQL, the plaintext MQTT listener, FastAPI, and the MQTT worker are only
reachable on Docker's private network. PostgreSQL is the source of truth;
Mosquitto only transports and temporarily queues messages.

## Prerequisites

- A Linux home server with Docker Engine and Docker Compose v2.
- Two DNS records pointing at the home connection, for example
  `mqtt.example.net` and `tracker.example.net`. Dynamic DNS is acceptable.
- Router forwarding for TCP `8883`, `80`, and `443`.
- A firewall allowing only those ports. Do not expose PostgreSQL (`5432`) or
  MQTT plaintext (`1883`).

## Bootstrap

From this directory:

```sh
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh mqtt.example.net tracker.example.net
docker compose config
docker compose up -d --build
docker compose ps
```

The bootstrap is idempotent: it does not replace existing secrets or the CA.
It creates a private CA and a broker certificate valid for the MQTT DNS name,
hashed Mosquitto credentials, database/API tokens, and a Caddy password hash.

Back up `secrets/` (including `mqtt_ca.key`) and the Docker volumes offline.
The CA private key must never be copied to a gateway.

## Generate the gateway header

Run this from the repository root, substituting the Wi-Fi details:

```sh
python3 deploy/scripts/render_firmware_secrets.py \
  --wifi-ssid 'farm-wifi' \
  --wifi-password 'replace-me' \
  --mqtt-host 'mqtt.example.net' \
  --mqtt-password-file deploy/secrets/mqtt_gateway_password.txt \
  --ca-file deploy/mosquitto/certs/ca.crt \
  --output ../meshtastic_fork/src/modules/irrigation/IrrigationGatewaySecrets.generated.h
```

The generated file is intentionally ignored by Git. Build and flash `hwt_gw`
after generating it. Keep the gateway username restricted to publish-only ACLs.

## Security and operations

- Rotate the Wi-Fi and MQTT credentials that were previously present in the
  PlatformIO file; they must be considered disclosed.
- Use a strong router/admin password and disable UPnP.
- Apply operating-system and container updates regularly.
- Back up PostgreSQL with `pg_dump`; do not treat Mosquitto persistence as a
  database backup.
- Review `docker compose logs mosquitto mqtt-worker api` after initial rollout.
- The dashboard certificate is managed automatically by Caddy. The MQTT
  certificate uses the private CA and is valid for 825 days; renew it before
  expiry and keep the same CA so gateways continue to trust it.

"""Long-running MQTT-to-PostgreSQL ingestion worker."""

import logging
import ssl

import paho.mqtt.client as mqtt

from app.config import settings
from app.database import Base, engine, session_local
from app.mqtt_codec import InvalidMqttMessage, normalize_mqtt_message
from app.services.ingestion import ingest_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("irrigation.mqtt")


def on_connect(
    client: mqtt.Client,
    userdata: object,
    flags: mqtt.ConnectFlags,
    reason_code: mqtt.ReasonCode,
    properties: mqtt.Properties | None,
) -> None:
    """Subscribe with QoS 1 after every successful connection."""

    del userdata, flags, properties
    if reason_code.is_failure:
        logger.error("MQTT connection rejected: %s", reason_code)
        return
    result, message_id = client.subscribe(settings.mqtt_topic, qos=settings.mqtt_qos)
    if result != mqtt.MQTT_ERR_SUCCESS:
        raise RuntimeError(f"MQTT subscribe failed with code {result}")
    logger.info("Subscribed to %s at QoS %d (mid=%d)", settings.mqtt_topic, settings.mqtt_qos, message_id)


def on_message(client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
    """Commit to PostgreSQL before acknowledging a QoS 1 delivery."""

    del userdata
    try:
        event = normalize_mqtt_message(message.topic, message.payload)
    except InvalidMqttMessage as exc:
        logger.warning("Discarding invalid MQTT message topic=%s: %s", message.topic, exc)
        client.ack(message.mid, message.qos)
        return

    db = session_local()
    try:
        inserted = ingest_event(db, event)
        client.ack(message.mid, message.qos)
        logger.info(
            "%s telemetry msg_id=%s tracker=%s",
            "Inserted" if inserted else "Deduplicated",
            event.msg_id,
            event.tracker_id,
        )
    except Exception:
        db.rollback()
        logger.exception("Database failure; MQTT message left unacknowledged for redelivery")
        client.disconnect()
    finally:
        db.close()


def build_client() -> mqtt.Client:
    """Configure a persistent MQTT 3.1.1 client with manual acknowledgements."""

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=settings.mqtt_client_id,
        clean_session=False,
        protocol=mqtt.MQTTv311,
        manual_ack=True,
    )
    if settings.mqtt_username:
        client.username_pw_set(settings.mqtt_username, settings.resolved_mqtt_password)
    if settings.mqtt_tls:
        client.tls_set(
            ca_certs=settings.mqtt_ca_file or None,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )
    client.reconnect_delay_set(min_delay=1, max_delay=60)
    client.on_connect = on_connect
    client.on_message = on_message
    return client


def main() -> None:
    """Create the schema and consume MQTT forever."""

    Base.metadata.create_all(bind=engine)
    client = build_client()
    logger.info("Connecting to MQTT %s:%d", settings.mqtt_host, settings.mqtt_port)
    client.connect(settings.mqtt_host, settings.mqtt_port, settings.mqtt_keepalive_seconds)
    client.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()

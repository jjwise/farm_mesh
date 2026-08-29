"""Long-running MQTT-to-PostgreSQL ingestion worker."""

import logging
import ssl
import time
from datetime import datetime, timedelta, timezone

import paho.mqtt.client as mqtt
from app.config import settings
from app.database import initialize_schema, session_local
from app.models import NodeCommandModel, NodeStateModel
from app.mqtt_codec import InvalidMqttMessage, normalize_mqtt_message
from app.services.commands import validate_topic_segment
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


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def retry_node_commands(client: mqtt.Client) -> None:
    """Retry the audited command outbox until a node acknowledges or the TTL expires."""

    now = datetime.now(timezone.utc)
    retry_before = now - timedelta(seconds=settings.command_retry_seconds)
    db = session_local()
    try:
        active = (
            db.query(NodeCommandModel)
            .filter(NodeCommandModel.status.in_(("PENDING", "SENT")))
            .order_by(NodeCommandModel.created_at.asc())
            .limit(100)
            .all()
        )
        for command in active:
            if _as_utc(command.expires_at) <= now:
                command.status = "EXPIRED"
                state = db.query(NodeStateModel).filter_by(tracker_id=command.tracker_id).one_or_none()
                if state is not None and state.last_command_id == command.command_id:
                    state.last_command_status = "EXPIRED"
                continue

            sent_at = _as_utc(command.sent_at) if command.sent_at else None
            if not client.is_connected() or (sent_at is not None and sent_at > retry_before):
                continue

            try:
                validate_topic_segment(command.farm_id, "farm_id")
                validate_topic_segment(command.tracker_id, "tracker_id")
                topic = f"farm/{command.farm_id}/nodes/{command.tracker_id}/commands"
                result = client.publish(
                    topic,
                    command.payload_json,
                    qos=settings.mqtt_command_qos,
                    retain=False,
                )
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    raise RuntimeError(f"MQTT publish returned {result.rc}")
                result.wait_for_publish(timeout=settings.mqtt_publish_timeout_seconds)
                if not result.is_published():
                    raise TimeoutError("MQTT command retry timed out")
                command.status = "SENT"
                command.sent_at = now
                command.error_message = ""
                state = db.query(NodeStateModel).filter_by(tracker_id=command.tracker_id).one_or_none()
                if state is not None and state.last_command_id == command.command_id:
                    state.last_command_status = "SENT"
                logger.info("Retried command id=%s target=%s", command.command_id, command.tracker_id)
            except ValueError as exc:
                command.status = "FAILED"
                command.error_message = str(exc)[:500]
            except Exception as exc:
                command.error_message = str(exc)[:500]
                logger.warning("Command retry failed id=%s: %s", command.command_id, exc)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Command outbox maintenance failed")
    finally:
        db.close()


def main() -> None:
    """Create the schema, ingest telemetry, and maintain the command outbox."""

    initialize_schema()
    client = build_client()
    logger.info("Connecting to MQTT %s:%d", settings.mqtt_host, settings.mqtt_port)
    client.connect(settings.mqtt_host, settings.mqtt_port, settings.mqtt_keepalive_seconds)
    client.loop_start()
    try:
        while True:
            retry_node_commands(client)
            time.sleep(max(1, settings.command_retry_seconds))
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()

import logging
import os
import signal
import threading

from app.db import Database
from app.messaging import MessagingProvider, WahaMessagingProvider
from app.planning import configured_generator
from app.planning_providers import PlanningError
from app.sharing import result_summary, viewer_link

logger = logging.getLogger(__name__)


def process_ack(database: Database, provider: MessagingProvider) -> bool:
    ack = database.claim_ack()
    if ack is None:
        return False
    try:
        provider.send_text(
            session=ack["session"], chat_id=ack["sender"],
            text=f"Tripse DEMO: request accepted. trip_id: {ack['trip_id']}. "
                 + ("Generation is MOCK ONLY; no places or routes are verified."
                  if os.getenv("PLANNING_MODE", "live") == "mock"
                  else "Preparing a draft; maps and limits will be checked."),
        )
    except Exception:
        # Do not log HTTP bodies, keys or sender numbers.
        logger.warning("WAHA acknowledgement deferred for trip %s", ack["trip_id"])
        database.finish_ack(ack, sent=False)
    else:
        database.finish_ack(ack, sent=True)
    return True


def process_result(database: Database, provider: MessagingProvider) -> bool:
    notification = database.claim_result()
    if notification is None:
        return False
    try:
        provider.send_text(session=notification["session"], chat_id=notification["sender"],
                           text=notification["text"])
    except Exception:
        logger.warning("WAHA result deferred for trip %s", notification["trip_id"])
        database.finish_result(notification, sent=False)
    else:
        database.finish_result(notification, sent=True)
    return True


def process_next(database: Database, generator=None) -> bool:
    job = database.claim_next()
    if job is None:
        return False
    try:
        result = (generator or configured_generator())(job["trip_id"], job["request_text"])
        token, url, expires_at = viewer_link()
        result.update(viewer_url=url, viewer_expires_at=expires_at)
        database.finish(job["trip_id"], result=result, viewer_token=token,
                        viewer_expires_at=expires_at, notification=result_summary(result))
    except Exception as error:
        logger.warning("Trip generation failed for %s (%s)", job["trip_id"], type(error).__name__)
        message = str(error) if isinstance(error, PlanningError) else "Trip generation failed. See worker logs."
        database.finish(job["trip_id"], error=message,
                        notification=f"Tripse: trip {job['trip_id']} failed. {message}")
    return True


def main():
    logging.basicConfig(level=logging.INFO)
    poll_seconds = float(os.getenv("WORKER_POLL_SECONDS", "1"))
    if not 0 < poll_seconds <= 60:
        raise ValueError("WORKER_POLL_SECONDS must be greater than 0 and at most 60")
    database = Database(os.getenv("DATABASE_PATH", "data/tripse.sqlite3"))
    database.initialize()
    database.recover_interrupted()
    provider = WahaMessagingProvider.from_env()
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    logger.info("Worker started (one worker only), planning mode: %s", os.getenv("PLANNING_MODE", "live"))
    while not stop.is_set():
        process_ack(database, provider)
        worked = process_next(database)
        process_result(database, provider)
        if not worked:
            stop.wait(poll_seconds)


if __name__ == "__main__":
    main()

"""Pipeline Orchestrator daemon entrypoint adhering to Documents 08 and 16."""

import asyncio
import logging
import signal
import sys

from packages.config.settings import settings
from packages.event_schema import RedisStreamBus
from services.orchestrator.pipeline import PipelineOrchestrator

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("orchestrator")


async def main() -> None:
    """Runs the Pipeline Orchestrator daemon."""
    logger.info("Initializing Pipeline Orchestrator daemon...")

    bus = RedisStreamBus()
    await bus.connect()

    orchestrator = PipelineOrchestrator(stream_bus=bus)
    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Received termination signal, shutting down orchestrator...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _signal_handler)

    logger.info("Pipeline Orchestrator running. Evaluating liveness and processing DLQ retries.")

    try:
        while not stop_event.is_set():
            # Periodic health check and DLQ retry loop
            try:
                orchestrator.health_monitor.evaluate_liveness()
                for meeting_id in list(orchestrator._active_pipelines):
                    await orchestrator.dlq_manager.poll_and_retry(meeting_id=meeting_id)
            except Exception as exc:
                logger.warning("Error in orchestrator periodic evaluation: %s", exc)

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
    finally:
        await bus.disconnect()
        logger.info("Pipeline Orchestrator disconnected from Redis bus.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Pipeline Orchestrator stopped by user.")

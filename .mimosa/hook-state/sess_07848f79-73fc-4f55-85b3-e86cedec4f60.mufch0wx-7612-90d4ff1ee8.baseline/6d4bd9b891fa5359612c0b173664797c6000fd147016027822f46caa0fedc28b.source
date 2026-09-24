"""Unified AI Fleet Worker Dispatcher.

Dispatches the appropriate AI worker process based on the `WORKER_TYPE` environment variable.
Supported worker types:
- `stt`: Speech-to-Text inference worker
- `translation`: Neural Machine Translation worker
- `tts`: Text-to-Speech synthesis worker
- `speaker`: Speaker diarization & voice profiling worker
- `assistant`: RAG meeting copilot worker
- `orchestrator`: Pipeline stream orchestrator & DLQ retry manager
"""

import asyncio
import os
import sys


def main() -> None:
    worker_type = os.getenv("WORKER_TYPE", sys.argv[1] if len(sys.argv) > 1 else "stt").lower()
    meeting_id = os.getenv("MEETING_ID", sys.argv[2] if len(sys.argv) > 2 else "default_meeting")

    # Pass meeting_id to sys.argv for child worker entrypoints
    sys.argv = [sys.argv[0], meeting_id]

    print(f"Starting unified worker runner: type={worker_type}, meeting={meeting_id}")

    if worker_type in ("stt", "stt_worker"):
        from services.stt_worker.main import main as worker_main
    elif worker_type in ("translation", "nmt", "translation_worker"):
        from services.translation_worker.main import main as worker_main
    elif worker_type in ("tts", "tts_worker"):
        from services.tts_worker.main import main as worker_main
    elif worker_type in ("speaker", "diarization", "speaker_worker"):
        from services.speaker_worker.main import main as worker_main
    elif worker_type in ("assistant", "rag", "assistant_worker"):
        from services.assistant_worker.main import main as worker_main
    elif worker_type in ("orchestrator", "pipeline"):
        from services.orchestrator.main import main as worker_main
    else:
        raise ValueError(f"Unknown WORKER_TYPE: {worker_type}")

    asyncio.run(worker_main())


if __name__ == "__main__":
    main()

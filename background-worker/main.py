"""
Background Worker — consumes tasks_queue. One queue, many job types,
dispatched internally by TASK_HANDLERS (the correct version of "one
queue shared across job types" — see docs/architecture.md). Handlers
(generate_pdf, send_whatsapp_notification, send_otp, ...) are
registered at kickoff; this file is the infra skeleton.
"""
import asyncio
import json
import os
import time

import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = "tasks_queue"
RESULT_TTL_SECONDS = 3600
HEARTBEAT_KEY = f"heartbeat:background-worker:{os.environ.get('HOSTNAME', 'unknown')}"

TASK_HANDLERS = {
    # "generate_pdf": handle_generate_pdf,
    # "send_whatsapp_notification": handle_send_whatsapp_notification,  # uses
    #     shared.whatsapp_client.send_whatsapp_message() — the output guard
    #     (docs/ai-system.md §5.1) is enforced inside that shared client, so
    #     handlers here don't need to call it separately.
    # "send_otp": handle_send_otp,
    # registered at kickoff
}


async def process_job(r: redis.Redis, job: dict):
    job_id = job["job_id"]
    handler = TASK_HANDLERS.get(job.get("type"))
    if handler is None:
        await r.set(f"result:{job_id}", json.dumps({"status": "error", "error": f"unknown task type: {job.get('type')}"}), ex=RESULT_TTL_SECONDS)
        return
    try:
        result = await handler(job)
        await r.set(f"result:{job_id}", json.dumps({"status": "done", "result": result}), ex=RESULT_TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001 — boundary catch, reported to caller
        await r.set(f"result:{job_id}", json.dumps({"status": "error", "error": str(exc)}), ex=RESULT_TTL_SECONDS)


async def heartbeat_loop(r: redis.Redis):
    while True:
        await r.set(HEARTBEAT_KEY, str(time.time()), ex=15)
        await asyncio.sleep(5)


async def main():
    r = redis.from_url(REDIS_URL)
    asyncio.create_task(heartbeat_loop(r))
    print(f"Background worker started, listening on '{QUEUE_NAME}'")
    while True:
        _, raw_job = await r.blpop(QUEUE_NAME)
        job = json.loads(raw_job)
        asyncio.create_task(process_job(r, job))


if __name__ == "__main__":
    asyncio.run(main())

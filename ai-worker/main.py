"""
AI Worker — consumes ai_queue, orchestrates via LangGraph/LangChain,
calls models via LiteLLM (docs/ai-system.md).

Infra skeleton: queue loop, concurrency cap, timeout, retry, heartbeat,
AI-config fetch, agent roles (PLA/RBAC), input/output guards, and
telemetry — all decided pre-hackathon per docs/ai-system.md. The
LangGraph workflow in run_graph() is domain-specific, defined at kickoff.
"""
import asyncio
import json
import os
import time

import httpx
import redis.asyncio as redis
from dotenv import load_dotenv

from shared.security_guards import input_guard, output_guard

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
MAIN_SERVICE_URL = os.environ.get("MAIN_SERVICE_URL", "http://main-service:8000")
QUEUE_NAME = "ai_queue"
CONCURRENCY_LIMIT = int(os.environ.get("AI_WORKER_CONCURRENCY", "5"))
JOB_TIMEOUT_SECONDS = int(os.environ.get("AI_JOB_TIMEOUT", "60"))
RESULT_TTL_SECONDS = 3600
CONFIG_CACHE_TTL_SECONDS = 30
HEARTBEAT_KEY = f"heartbeat:ai-worker:{os.environ.get('HOSTNAME', 'unknown')}"

semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
_config_cache = {"data": None, "fetched_at": 0.0}

# --- Agent roles (RBAC) — docs/ai-system.md §4.2. Code, not Dynamic
# Config: permissions shouldn't be one Django-Admin click away from
# being loosened. Tool names filled in at kickoff; each graph node is
# bound to exactly one role's tool list, never the full registry.
AGENT_ROLES = {
    "retriever":       {"tools": [], "can_act_externally": False},
    "responder":       {"tools": [], "can_act_externally": False},
    "action_executor": {"tools": [], "can_act_externally": True},
}


async def get_ai_config() -> dict:
    """Fetched from Main Service, not Postgres directly — cached briefly to avoid a round-trip per call."""
    now = time.time()
    if _config_cache["data"] is None or now - _config_cache["fetched_at"] > CONFIG_CACHE_TTL_SECONDS:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{MAIN_SERVICE_URL}/api/internal/ai-config")
            response.raise_for_status()
            _config_cache["data"] = response.json()["data"]
            _config_cache["fetched_at"] = now
    return _config_cache["data"]


async def log_ai_call(**fields) -> None:
    """Telemetry — docs/ai-system.md §4.4/§6.2. Posted to Main Service, not
    written to Postgres directly (only Main Service touches Postgres)."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{MAIN_SERVICE_URL}/api/internal/ai-calls", json=fields)
    except Exception as exc:  # noqa: BLE001 — telemetry failure must never break the job
        print(f"telemetry log failed (non-fatal): {exc}")


async def run_graph(job: dict, role: str):
    """TODO (kickoff): build the LangGraph workflow for this job's task type,
    using AGENT_ROLES[role]["tools"] to bind only that role's permitted tools."""
    raise NotImplementedError("Define the LangGraph workflow at kickoff")


async def process_job(r: redis.Redis, job: dict):
    job_id = job["job_id"]
    agent_role = job.get("agent_role", "responder")
    started_at = time.time()

    async with semaphore:
        try:
            guard = input_guard(job.get("input", ""))
            if not guard["ok"]:
                raise ValueError(f"input rejected: {guard['reason']}")
            if guard.get("flagged"):
                print(f"[security] input flagged for job {job_id}: {guard['reason']}")

            result = await asyncio.wait_for(run_graph(job, role=agent_role), timeout=JOB_TIMEOUT_SECONDS)

            out_text = result if isinstance(result, str) else json.dumps(result)
            out_guard = output_guard(out_text)
            if not out_guard["ok"]:
                raise ValueError(f"output blocked: {out_guard['reason']}")

            await r.set(f"result:{job_id}", json.dumps({"status": "done", "result": result}), ex=RESULT_TTL_SECONDS)
            await log_ai_call(
                job_id=job_id, agent_role=agent_role, status="done",
                latency_ms=int((time.time() - started_at) * 1000),
                flagged_input=guard.get("flagged", False),
            )
        except Exception as exc:  # noqa: BLE001 — boundary catch, reported to caller
            await r.set(f"result:{job_id}", json.dumps({"status": "error", "error": str(exc)}), ex=RESULT_TTL_SECONDS)
            await log_ai_call(
                job_id=job_id, agent_role=agent_role, status="error",
                latency_ms=int((time.time() - started_at) * 1000), error=str(exc),
            )


async def heartbeat_loop(r: redis.Redis):
    while True:
        await r.set(HEARTBEAT_KEY, str(time.time()), ex=15)
        await asyncio.sleep(5)


async def main():
    r = redis.from_url(REDIS_URL)
    asyncio.create_task(heartbeat_loop(r))
    print(f"AI worker started, listening on '{QUEUE_NAME}'")
    while True:
        _, raw_job = await r.blpop(QUEUE_NAME)
        job = json.loads(raw_job)
        asyncio.create_task(process_job(r, job))


if __name__ == "__main__":
    asyncio.run(main())

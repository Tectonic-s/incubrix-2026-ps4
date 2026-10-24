"""FastAPI application entrypoint conforming to IncuBrix Integration Standards."""
import asyncio
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from src.config import settings
from src.connectors.base import BaseConnector, ConnectorException
from src.connectors.registry import registry
from src.database import get_db, init_db
from src.engine.catalogue_importer import catalogue_importer
from src.engine.certification import certification_harness
from src.engine.recertification import recertification_scheduler
from src.engine.recommender import recommendation_engine
from src.engine.rules_capture import rules_capture_engine
from src.engine.rules_engine import rules_engine
from src.engine.tailoring import tailoring_engine
from src.logger import current_correlation_id, current_job_id, get_logger, logger
from src.models.connector import (
    BuildAssistPackRequest,
    Connection,
    DeleteRequest,
    Destination,
    FetchMetricsRequest,
    GetStatusRequest,
    PublishRequest,
    PublishResponse,
    RefreshAuthRequest,
    Rendition,
    ValidateRequest,
)
from src.models.manifest import JobResponse, JobStatus, OutputManifest
from src.storage import fetch_or_read_input, get_storage

app = FastAPI(
    title="IncuBrix Long-Tail Distribution Network Service",
    description="Containerised distribution connector service conforming to IncuBrix Connector Contract and Integration Standards.",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = get_storage()


@app.on_event("startup")
def on_startup():
    init_db()
    from pathlib import Path
    cat_file = Path("./data/real_catalogue_150.csv")
    if cat_file.exists():
        with get_db() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM destinations")
            if cur.fetchone()[0] == 0:
                with open(cat_file, "r", encoding="utf-8") as f:
                    catalogue_importer.import_csv(f.read())
    logger.info("IncuBrix Distribution Service started.")


# --- Request Middleware: Correlation ID & Error Handling ---
@app.middleware("http")
async def correlation_and_error_middleware(request: Request, call_next):
    corr_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
    token_corr = current_correlation_id.set(corr_id)

    start_time = time.time()
    try:
        response = await call_next(request)
        response.headers["X-Correlation-Id"] = corr_id
        return response
    except ConnectorException as ce:
        logger.warning(f"ConnectorException: {ce.code} - {ce.message}")
        return JSONResponse(
            status_code=ce.status_code,
            content=ce.to_dict(),
            headers={"X-Correlation-Id": corr_id},
        )
    except Exception as exc:
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "PLATFORM_UNAVAILABLE",
                    "message": "Internal service error occurred.",
                    "retryable": True,
                    "details": str(exc),
                }
            },
            headers={"X-Correlation-Id": corr_id},
        )
    finally:
        current_correlation_id.reset(token_corr)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    corr_id = current_correlation_id.get() or "none"
    errors = exc.errors()
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "DEST_SPEC_VIOLATION",
                "message": "Request validation failed.",
                "retryable": False,
                "details": errors,
            }
        },
        headers={"X-Correlation-Id": corr_id},
    )


# --- Health & Readiness Endpoints (Integration Standard Point 8) ---
@app.get("/health")
@app.get("/ready")
@app.get("/api/v1/health")
@app.get("/api/v1/ready")
async def health_check():
    return {
        "status": "healthy",
        "service": "incubrix-ps4-distribution",
        "simulation_mode": settings.SIMULATION_MODE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# --- Local Storage Download Route (Integration Standard Point 7) ---
@app.get("/api/v1/storage/{storage_key}")
async def get_storage_file(storage_key: str):
    try:
        data = storage.get(storage_key)
        return Response(content=data, media_type="application/octet-stream")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Artifact not found")


# --- Appendix A Connector Endpoints: POST /connector/v1/{connector_key}/{method} ---
@app.post("/connector/v1/{connector_key}/validate")
@app.post("/api/v1/connector/{connector_key}/validate")
async def connector_validate(connector_key: str, req: ValidateRequest):
    conn = registry.get(connector_key)
    return conn.validate(req.rendition, req.destination, req.connection)


@app.post("/connector/v1/{connector_key}/publish")
@app.post("/api/v1/connector/{connector_key}/publish")
async def connector_publish(
    connector_key: str,
    req: PublishRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    conn = registry.get(connector_key)
    return await conn.publish(
        req.rendition,
        req.destination,
        req.connection,
        idempotency_key=idempotency_key or req.idempotency_key,
    )


@app.post("/connector/v1/{connector_key}/get_status")
@app.post("/api/v1/connector/{connector_key}/get_status")
async def connector_get_status(connector_key: str, req: GetStatusRequest):
    conn = registry.get(connector_key)
    return await conn.get_status(req.platform_post_id, req.connection)


@app.post("/connector/v1/{connector_key}/delete")
@app.post("/api/v1/connector/{connector_key}/delete")
async def connector_delete(connector_key: str, req: DeleteRequest):
    conn = registry.get(connector_key)
    return await conn.delete(req.platform_post_id, req.connection)


@app.post("/connector/v1/{connector_key}/fetch_metrics")
@app.post("/api/v1/connector/{connector_key}/fetch_metrics")
async def connector_fetch_metrics(connector_key: str, req: FetchMetricsRequest):
    conn = registry.get(connector_key)
    return await conn.fetch_metrics(req.platform_post_id, req.connection, req.since)


@app.post("/connector/v1/{connector_key}/refresh_auth")
@app.post("/api/v1/connector/{connector_key}/refresh_auth")
async def connector_refresh_auth(connector_key: str, req: RefreshAuthRequest):
    conn = registry.get(connector_key)
    return await conn.refresh_auth(req.connection)


@app.post("/connector/v1/{connector_key}/build_assist_pack")
@app.post("/api/v1/connector/{connector_key}/build_assist_pack")
async def connector_build_assist_pack(connector_key: str, req: BuildAssistPackRequest):
    conn = registry.get(connector_key)
    return await conn.build_assist_pack(req.rendition, req.destination)


# --- Manifest & Connector Registry ---
@app.get("/api/v1/connectors")
async def list_connectors():
    return registry.list_all()


@app.get("/api/v1/connectors/{connector_key}/manifest")
async def get_connector_manifest(connector_key: str):
    conn = registry.get(connector_key)
    return conn.manifest


# --- Destinations Catalogue Endpoints (Must-Have 3: Configuration, not code) ---
@app.get("/api/v1/destinations")
async def list_destinations(
    platform_key: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    query = "SELECT * FROM destinations WHERE 1=1"
    params = []
    if platform_key:
        query += " AND platform_key = ?"
        params.append(platform_key)
    if level:
        query += " AND level = ?"
        params.append(level)
    query += " ORDER BY relevance_score DESC, est_audience DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_db() as conn:
        cur = conn.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r["audience_tags"] = json.loads(r["audience_tags"]) if r["audience_tags"] else []
            r["self_promo_allowed"] = bool(r["self_promo_allowed"])
            r["disclosure_required"] = bool(r["disclosure_required"])
            r["automation_allowed"] = bool(r["automation_allowed"])
    return rows


@app.post("/api/v1/destinations")
async def create_destination(dest: Destination):
    now = datetime.now(timezone.utc).isoformat()
    dest_id = dest.id or str(uuid.uuid4())
    norm_url = catalogue_importer.normalise_url(dest.url)

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO destinations (
                id, name, url, platform_key, surface, category, audience_tags, language,
                geo, est_audience, rules_url, frequency_cap, self_promo_allowed, link_policy,
                disclosure_required, automation_allowed, connector_key, relevance_score,
                relevance_reason, level, last_certified_at, config_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url, platform_key) DO UPDATE SET
                name=excluded.name,
                surface=excluded.surface,
                category=excluded.category,
                audience_tags=excluded.audience_tags,
                frequency_cap=excluded.frequency_cap,
                self_promo_allowed=excluded.self_promo_allowed,
                link_policy=excluded.link_policy,
                disclosure_required=excluded.disclosure_required,
                relevance_score=excluded.relevance_score,
                relevance_reason=excluded.relevance_reason,
                config_json=excluded.config_json,
                updated_at=excluded.updated_at
            """,
            (
                dest_id,
                dest.name,
                norm_url,
                dest.platform_key,
                dest.surface,
                dest.category,
                json.dumps(dest.audience_tags),
                dest.language,
                dest.geo,
                dest.est_audience,
                dest.rules_url or f"{norm_url}/guidelines",
                dest.frequency_cap,
                1 if dest.self_promo_allowed else 0,
                dest.link_policy,
                1 if dest.disclosure_required else 0,
                1 if dest.automation_allowed else 0,
                dest.connector_key,
                dest.relevance_score,
                dest.relevance_reason,
                dest.level,
                dest.last_certified_at,
                json.dumps(dest.config),
                now,
                now,
            ),
        )
    return {"id": dest_id, "status": "created", "url": norm_url}


# --- Background Job Engine (Integration Standard Points 3 & 4) ---
async def execute_publication_job(
    job_id: str,
    rendition: Rendition,
    destination_id: str,
    connection: Connection,
    callback_url: Optional[str] = None,
    correlation_id: Optional[str] = None,
):
    token_job = current_job_id.set(job_id)
    token_corr = current_correlation_id.set(correlation_id)
    start_time = time.time()
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        # Step 1: Update status to running (25%)
        with get_db() as conn:
            conn.execute(
                "UPDATE jobs SET status = 'running', progress = 25, updated_at = ? WHERE job_id = ?",
                (now_iso, job_id),
            )

        # Retrieve destination
        with get_db() as conn:
            cur = conn.execute("SELECT * FROM destinations WHERE id = ? OR name = ?", (destination_id, destination_id))
            row = cur.fetchone()
            if not row:
                cur = conn.execute("SELECT * FROM destinations WHERE connector_key = ? LIMIT 1", (destination_id,))
                row = cur.fetchone()
            if not row:
                dest = Destination(
                    id=destination_id,
                    name=destination_id,
                    url=f"https://{destination_id.lower().replace(' ', '')}.example.com",
                    platform_key="discourse",
                    connector_key="discourse",
                )
            else:
                dest = Destination(
                    id=row["id"],
                    name=row["name"],
                    url=row["url"],
                    platform_key=row["platform_key"],
                    surface=row["surface"],
                    category=row["category"],
                    audience_tags=json.loads(row["audience_tags"]) if row["audience_tags"] else [],
                    language=row["language"],
                    geo=row["geo"],
                    est_audience=row["est_audience"],
                    rules_url=row["rules_url"],
                    frequency_cap=row["frequency_cap"],
                    self_promo_allowed=bool(row["self_promo_allowed"]),
                    link_policy=row["link_policy"],
                    disclosure_required=bool(row["disclosure_required"]),
                    automation_allowed=bool(row["automation_allowed"]),
                    connector_key=row["connector_key"],
                    relevance_score=row["relevance_score"],
                    relevance_reason=row["relevance_reason"],
                    level=row["level"],
                    last_certified_at=row["last_certified_at"],
                )

        # Step 2: Posting-Rules check (50%)
        with get_db() as conn:
            conn.execute(
                "UPDATE jobs SET progress = 50, updated_at = ? WHERE job_id = ?",
                (datetime.now(timezone.utc).isoformat(), job_id),
            )
        rules_engine.check_rules(rendition, dest)

        # Step 3: Tailoring (70%)
        tailored_rendition = tailoring_engine.tailor(rendition, dest)

        # Step 4: Publish via connector (85%)
        with get_db() as conn:
            conn.execute(
                "UPDATE jobs SET progress = 85, updated_at = ? WHERE job_id = ?",
                (datetime.now(timezone.utc).isoformat(), job_id),
            )
        connector = registry.get(dest.connector_key)
        pub_result = await connector.publish(tailored_rendition, dest, connection, idempotency_key=job_id)

        # Record post in DB
        post_record_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO posts (id, destination_id, platform_post_id, idempotency_key, status, title, live_url, rendition_json, published_at)
                VALUES (?, ?, ?, ?, 'published', ?, ?, ?, ?)
                """,
                (
                    post_record_id,
                    dest.id,
                    pub_result.platform_post_id,
                    job_id,
                    tailored_rendition.title,
                    pub_result.live_url,
                    tailored_rendition.model_dump_json(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

        # Step 5: Save manifest and output artifact (Integration Standard Point 9)
        elapsed_ms = (time.time() - start_time) * 1000
        manifest = OutputManifest(
            models_providers={
                "connector": dest.connector_key,
                "ai_adapter": settings.AI_PROVIDER,
            },
            version="1.0.0",
            settings={
                "simulation_mode": settings.SIMULATION_MODE,
                "frequency_cap": dest.frequency_cap,
            },
            timings_ms={"total_pipeline_ms": round(elapsed_ms, 2)},
            cost_estimate_usd=0.0001,
            warnings=[],
        )

        manifest_key, manifest_url = storage.save(
            f"manifest_{job_id}.json",
            manifest.model_dump_json(),
        )

        result_payload = {
            "post_id": post_record_id,
            "platform_post_id": pub_result.platform_post_id,
            "live_url": pub_result.live_url,
            "status": pub_result.status,
            "manifest_url": manifest_url,
            "destination_name": dest.name,
            "tailored_rendition": tailored_rendition.model_dump(),
        }

        # Step 6: Mark succeeded (100%)
        with get_db() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'succeeded', progress = 100, result_json = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (json.dumps(result_payload), datetime.now(timezone.utc).isoformat(), job_id),
            )

        # Trigger signed HMAC callback if configured
        if callback_url:
            await send_signed_callback(callback_url, job_id, "succeeded", result_payload)

    except ConnectorException as ce:
        error_payload = ce.to_dict()["error"]
        with get_db() as conn:
            conn.execute(
                "UPDATE jobs SET status = 'failed', error_json = ?, updated_at = ? WHERE job_id = ?",
                (json.dumps(error_payload), datetime.now(timezone.utc).isoformat(), job_id),
            )
        if callback_url:
            await send_signed_callback(callback_url, job_id, "failed", {"error": error_payload})
    except Exception as exc:
        error_payload = {
            "code": "PLATFORM_UNAVAILABLE",
            "message": str(exc),
            "retryable": True,
        }
        with get_db() as conn:
            conn.execute(
                "UPDATE jobs SET status = 'failed', error_json = ?, updated_at = ? WHERE job_id = ?",
                (json.dumps(error_payload), datetime.now(timezone.utc).isoformat(), job_id),
            )
        if callback_url:
            await send_signed_callback(callback_url, job_id, "failed", {"error": error_payload})
    finally:
        current_job_id.reset(token_job)
        current_correlation_id.reset(token_corr)


async def send_signed_callback(callback_url: str, job_id: str, status: str, payload: Dict[str, Any]):
    """Sends webhook callback signed with HMAC-SHA256 (Integration Standard Point 3)."""
    body = json.dumps({"job_id": job_id, "status": status, "payload": payload}).encode("utf-8")
    signature = "sha256=" + hmac.new(settings.WEBHOOK_HMAC_SECRET.encode(), body, hashlib.sha256).hexdigest()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(callback_url, content=body, headers={"X-IncuBrix-Signature": signature, "Content-Type": "application/json"})
    except Exception as e:
        logger.warning(f"Callback delivery to {callback_url} failed: {e}")


# --- Primary Publish Endpoint (202 Job-based + Safe Retries) ---
class PublishJobRequest(BaseModel):
    rendition: Rendition
    destination_id: str
    connection: Optional[Connection] = None
    callback_url: Optional[str] = None


@app.post("/api/v1/publish", status_code=202)
async def publish_content(
    req: PublishJobRequest,
    background_tasks: BackgroundTasks,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    conn_obj = req.connection or Connection()
    now_iso = datetime.now(timezone.utc).isoformat()
    corr_id = current_correlation_id.get() or str(uuid.uuid4())

    # Safe Retries (Integration Standard Point 4):
    if idempotency_key:
        with get_db() as conn:
            cur = conn.execute("SELECT * FROM jobs WHERE idempotency_key = ?", (idempotency_key,))
            existing = cur.fetchone()
            if existing:
                res_links = json.loads(existing["result_json"]) if existing["result_json"] else None
                err_dict = json.loads(existing["error_json"]) if existing["error_json"] else None
                return JobResponse(
                    job_id=existing["job_id"],
                    status=JobStatus(existing["status"]),
                    progress=existing["progress"],
                    result_links=res_links,
                    error=err_dict,
                )

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO jobs (job_id, idempotency_key, status, progress, callback_url, correlation_id, created_at, updated_at)
            VALUES (?, ?, 'queued', 0, ?, ?, ?, ?)
            """,
            (job_id, idempotency_key, req.callback_url, corr_id, now_iso, now_iso),
        )

    background_tasks.add_task(
        execute_publication_job,
        job_id,
        req.rendition,
        req.destination_id,
        conn_obj,
        req.callback_url,
        corr_id,
    )

    return JobResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        progress=0,
    )


@app.get("/api/v1/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        res_links = json.loads(row["result_json"]) if row["result_json"] else None
        err_dict = json.loads(row["error_json"]) if row["error_json"] else None
        return JobResponse(
            job_id=row["job_id"],
            status=JobStatus(row["status"]),
            progress=row["progress"],
            result_links=res_links,
            error=err_dict,
        )


# --- Certification Harness Endpoint ---
class CertifyRequest(BaseModel):
    destination_id: str
    connection: Optional[Connection] = None


@app.post("/api/v1/certify")
async def run_certification(req: CertifyRequest):
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM destinations WHERE id = ? OR name = ?", (req.destination_id, req.destination_id))
        row = cur.fetchone()
        if not row:
            raise ConnectorException("DEST_SPEC_VIOLATION", f"Destination {req.destination_id} not found")
        dest = Destination(
            id=row["id"],
            name=row["name"],
            url=row["url"],
            platform_key=row["platform_key"],
            surface=row["surface"],
            category=row["category"],
            audience_tags=json.loads(row["audience_tags"]) if row["audience_tags"] else [],
            language=row["language"],
            geo=row["geo"],
            est_audience=row["est_audience"],
            rules_url=row["rules_url"],
            frequency_cap=row["frequency_cap"],
            self_promo_allowed=bool(row["self_promo_allowed"]),
            link_policy=row["link_policy"],
            disclosure_required=bool(row["disclosure_required"]),
            automation_allowed=bool(row["automation_allowed"]),
            connector_key=row["connector_key"],
            relevance_score=row["relevance_score"],
            relevance_reason=row["relevance_reason"],
            level=row["level"],
            last_certified_at=row["last_certified_at"],
        )

    conn_obj = req.connection or Connection(base_url=dest.url)
    evidence = await certification_harness.certify_destination(dest, conn_obj)
    return evidence


# --- Catalogue Import Endpoint (Advanced: CSV upload or URL) ---
@app.post("/api/v1/catalogue/import")
async def import_catalogue(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
):
    csv_text = ""
    if file:
        content_bytes = await file.read()
        csv_text = content_bytes.decode("utf-8", errors="replace")
    elif url:
        csv_text = await fetch_or_read_input(url)
    else:
        raise ConnectorException("DEST_SPEC_VIOLATION", "Either file upload or URL must be provided.")

    report = catalogue_importer.import_csv(csv_text)
    return report


# --- Rules Capture & Human Confirmation Endpoints ---
class ProposeRulesRequest(BaseModel):
    community_url: str
    rules_text_or_url: Optional[str] = None


@app.post("/api/v1/rules/propose")
async def propose_rules(req: ProposeRulesRequest):
    return await rules_capture_engine.propose_rules(req.community_url, req.rules_text_or_url)


class ConfirmRulesRequest(BaseModel):
    proposal_id: str
    confirmed_rules: Dict[str, Any]
    destination_id: Optional[str] = None


@app.post("/api/v1/rules/confirm")
async def confirm_rules(req: ConfirmRulesRequest):
    return rules_capture_engine.confirm_rules(req.proposal_id, req.confirmed_rules, req.destination_id)


# --- Recommendation Endpoint (Outstanding Level) ---
class RecommendRequest(BaseModel):
    rendition: Rendition
    top_k: int = 10


@app.post("/api/v1/recommend")
async def recommend_destinations(req: RecommendRequest):
    ranked = recommendation_engine.rank_destinations(req.rendition, top_k=req.top_k)
    return {"recommendations": ranked, "count": len(ranked)}


# --- Recertification Endpoint (Outstanding Level) ---
@app.post("/api/v1/recertify")
async def trigger_recertification(force_all: bool = Query(False)):
    res = await recertification_scheduler.run_recertification(force_all=force_all)
    return res

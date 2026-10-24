"""Mock Platform Server simulating Discourse, Lemmy, Dev.to, Ghost, Webhooks, Slack, etc."""
import asyncio
import json
from typing import Any, Dict
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse

mock_app = FastAPI(title="IncuBrix Mock Platform Test Server")

# In-memory stores for mock state
posts_store: Dict[str, Dict[str, Any]] = {}
idempotency_store: Dict[str, Dict[str, Any]] = {}


@mock_app.middleware("http")
async def simulation_interceptor(request: Request, call_next):
    # Check for forced test headers
    force_err = request.headers.get("X-Force-Error") or request.query_params.get("force_error")
    if force_err == "429":
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded. Try again later."},
            headers={"Retry-After": "3"},
        )
    if force_err == "401":
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized: Token expired or invalid."},
        )
    if force_err == "422":
        return JSONResponse(
            status_code=422,
            content={"error": "Unprocessable entity: Content violates community spam filter."},
        )
    if force_err == "timeout":
        await asyncio.sleep(15)  # Simulate network timeout

    # Safe retry & idempotency tracking
    idempotency_key = request.headers.get("Idempotency-Key")
    if request.method == "POST" and idempotency_key:
        if idempotency_key in idempotency_store:
            saved = idempotency_store[idempotency_key]
            return JSONResponse(status_code=saved["status_code"], content=saved["content"])

    response = await call_next(request)
    return response


# --- Discourse Mock Routes ---
@mock_app.post("/posts.json")
async def mock_discourse_publish(request: Request):
    idemp_key = request.headers.get("Idempotency-Key")
    body = await request.json()
    
    # Check schema drift simulation
    if request.headers.get("X-Simulate-Schema-Drift") == "true":
        return {"unexpected_renamed_field": 9999, "status": "ok"}

    post_id = len(posts_store) + 101
    topic_id = len(posts_store) + 501
    res_data = {
        "id": post_id,
        "topic_id": topic_id,
        "topic_slug": "incubrix-test-topic",
        "raw": body.get("raw", ""),
    }
    posts_store[str(post_id)] = res_data
    if idemp_key:
        idempotency_store[idemp_key] = {"status_code": 200, "content": res_data}
    return res_data


@mock_app.get("/posts/{post_id}.json")
async def mock_discourse_get(post_id: str):
    if post_id not in posts_store:
        raise HTTPException(status_code=404, detail="Post not found")
    data = posts_store[post_id]
    return {
        "id": int(post_id),
        "topic_id": data.get("topic_id", 501),
        "reads": 142,
        "like_count": 18,
        "reply_count": 5,
        "clicks": 12,
    }


@mock_app.delete("/posts/{post_id}.json")
async def mock_discourse_delete(post_id: str):
    if post_id in posts_store:
        del posts_store[post_id]
    return Response(status_code=204)


# --- Lemmy Mock Routes ---
@mock_app.post("/api/v3/post")
async def mock_lemmy_publish(request: Request):
    body = await request.json()
    post_id = len(posts_store) + 201
    res_data = {
        "post_view": {
            "post": {"id": post_id, "name": body.get("name")},
            "counts": {"score": 15, "upvotes": 15, "comments": 3},
        }
    }
    posts_store[str(post_id)] = res_data
    return res_data


@mock_app.get("/api/v3/post")
async def mock_lemmy_get(id: int):
    post_id = str(id)
    if post_id not in posts_store:
        raise HTTPException(status_code=404, detail="Lemmy post not found")
    return posts_store[post_id]


@mock_app.post("/api/v3/post/delete")
async def mock_lemmy_delete(request: Request):
    body = await request.json()
    post_id = str(body.get("post_id"))
    if post_id in posts_store:
        del posts_store[post_id]
    return {"post_view": {"post": {"id": int(post_id), "deleted": True}}}


# --- Dev.to Mock Routes ---
@mock_app.post("/articles")
async def mock_devto_publish(request: Request):
    body = await request.json()
    art = body.get("article", {})
    post_id = len(posts_store) + 301
    res_data = {
        "id": post_id,
        "title": art.get("title"),
        "url": f"https://dev.to/user/article-{post_id}",
        "page_views_count": 350,
        "public_reactions_count": 42,
        "comments_count": 8,
    }
    posts_store[str(post_id)] = res_data
    return res_data


@mock_app.get("/articles/{article_id}")
async def mock_devto_get(article_id: str):
    if article_id not in posts_store:
        raise HTTPException(status_code=404, detail="Article not found")
    return posts_store[article_id]


@mock_app.delete("/articles/{article_id}")
async def mock_devto_delete(article_id: str):
    if article_id in posts_store:
        del posts_store[article_id]
    return Response(status_code=204)


# --- Ghost Mock Routes ---
@mock_app.post("/ghost/api/admin/posts/")
async def mock_ghost_publish(request: Request):
    body = await request.json()
    post_in = body.get("posts", [{}])[0]
    post_id = f"ghost_{len(posts_store) + 401}"
    res_data = {
        "posts": [{
            "id": post_id,
            "title": post_in.get("title"),
            "slug": f"post-{post_id}",
            "url": f"https://blog.example.com/{post_id}",
            "count": {"views": 480, "likes": 35, "clicks": 64},
        }]
    }
    posts_store[post_id] = res_data
    return res_data


@mock_app.get("/ghost/api/admin/posts/{post_id}/")
async def mock_ghost_get(post_id: str):
    if post_id not in posts_store:
        raise HTTPException(status_code=404, detail="Ghost post not found")
    return posts_store[post_id]


@mock_app.delete("/ghost/api/admin/posts/{post_id}/")
async def mock_ghost_delete(post_id: str):
    if post_id in posts_store:
        del posts_store[post_id]
    return Response(status_code=204)


# --- Generic Webhook Mock Receiver ---
@mock_app.post("/webhook/receiver")
async def mock_webhook_receive(request: Request):
    # Verify HMAC signature header presence
    sig = request.headers.get("X-IncuBrix-Signature")
    if not sig:
        raise HTTPException(status_code=401, detail="Missing X-IncuBrix-Signature header")
    body = await request.json()
    post_id = f"wh_{len(posts_store) + 501}"
    res_data = {"id": post_id, "status": "received", "url": f"https://partner.example.com/events/{post_id}"}
    posts_store[post_id] = res_data
    return res_data


@mock_app.post("/webhook/receiver/revoke")
async def mock_webhook_revoke(request: Request):
    return {"revoked": True}

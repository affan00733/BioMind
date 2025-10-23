from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

from pipeline.embed_to_datapoints import main as run_embed

app = FastAPI()


@app.post("/run")
async def run(request: Request):
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    limit = int(body.get("limit", os.getenv("EMBED_LIMIT", "2000")))
    batch = int(body.get("batch_size", os.getenv("EMBED_BATCH", "256")))
    run_embed(batch_size=batch, limit=limit)
    return JSONResponse({"status": "ok", "limit": limit, "batch_size": batch})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))

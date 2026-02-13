from fastapi import FastAPI, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import os

from ai_engine import analyze_images
from database import (
    save_analysis,
    get_user_scores,
    get_user_analysis,
    get_leaderboard,
    get_admin_analytics
)

app = FastAPI(title="AI Quality Assurance API")

# -----------------------------
# CORS (Allow Frontend Access)
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# -----------------------------
# Health Check Route
# -----------------------------
@app.get("/")
async def root():
    return {"message": "AI Quality Assurance API is running"}


# -----------------------------
# Analyze Endpoint
# -----------------------------
@app.post("/analyze")
async def analyze(
    user_id: str = Form(...),
    before_image: UploadFile = File(...),
    after_image: UploadFile = File(...)
):
    try:
        start_time = time.time()

        before_path = os.path.join(UPLOAD_FOLDER, before_image.filename)
        after_path = os.path.join(UPLOAD_FOLDER, after_image.filename)

        with open(before_path, "wb") as f:
            f.write(await before_image.read())

        with open(after_path, "wb") as f:
            f.write(await after_image.read())

        result = analyze_images(before_path, after_path)

        processing_time = round((time.time() - start_time) * 1000, 2)
        result["processing_time_ms"] = processing_time

        previous_scores = get_user_scores(user_id)

        if previous_scores:
            trust_score = round(sum(previous_scores) / len(previous_scores), 2)
        else:
            trust_score = result["quality_score"]

        result["trust_score"] = trust_score
        result["user_id"] = user_id

        save_analysis(result)

        # Remove non-serializable fields
        result.pop("timestamp", None)
        result.pop("_id", None)

        return JSONResponse(content=result)

    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


# -----------------------------
# User Analytics Endpoint
# -----------------------------
@app.get("/user-analysis")
async def user_analysis(user_id: str = Query(...)):
    try:
        data = get_user_analysis(user_id)

        if not data:
            return JSONResponse(
                content={"message": "No records found for this user"},
                status_code=404
            )

        return JSONResponse(content=data)

    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


# -----------------------------
# Leaderboard Endpoint
# -----------------------------
@app.get("/leaderboard")
async def leaderboard():
    try:
        data = get_leaderboard(top_n=5)

        if not data:
            return JSONResponse(
                content={"message": "No users found"},
                status_code=404
            )

        return JSONResponse(content=data)

    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


# -----------------------------
# Admin Analytics Endpoint
# -----------------------------
@app.get("/admin-analytics")
async def admin_analytics():
    try:
        data = get_admin_analytics()

        if not data:
            return JSONResponse(
                content={"message": "No platform data available"},
                status_code=404
            )

        return JSONResponse(content=data)

    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

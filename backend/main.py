# backend/main.py
from fastapi import FastAPI, UploadFile, File
from typing import List
from io import StringIO
import pandas as pd

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "CloudSaver (CS) backend running"}

# React가 3000번 포트에서 올 거라 CORS 열어둠
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze")
async def analyze(files: List[UploadFile] = File(...)):
    frames = []
    for f in files:
        content = await f.read()
        df = pd.read_csv(StringIO(content.decode("utf-8")))
        df["source"] = f.filename
        frames.append(df)

    data = pd.concat(frames, ignore_index=True)

    suggestions = []
    if "cpu_avg" in data.columns:
        r1 = data[(data["cpu_avg"] < 3) & (data.get("days", 7) >= 7)]
        for _, row in r1.iterrows():
            suggestions.append({
                "service": row.get("service", "unknown"),
                "action": "다운사이징 추천",
                "estimated_saving": float(row.get("cost", 0)) * 0.4,
                "source": row["source"],
                "reason": "CPU 3% 미만 장기 유지"
            })

    total_saving = sum(s["estimated_saving"] for s in suggestions)

    return {
        "total_saving": total_saving,
        "currency": "USD",
        "count": len(suggestions),
        "suggestions": suggestions
    }

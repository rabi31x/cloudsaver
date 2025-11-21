from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from io import StringIO

import pandas as pd
import math

# --------------------------------------
# FastAPI 기본 세팅
# --------------------------------------
app = FastAPI(
    title="CloudSaver (CS) Backend",
    description="멀티 클라우드 비용 CSV를 분석해서 절감 제안을 반환하는 API",
    version="0.1.0",
)

# 프론트엔드 도메인 허용 (개발용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React 개발 서버
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------
# Pydantic 모델 (응답 스키마)
# --------------------------------------
class Suggestion(BaseModel):
    cloud: str
    category: str
    service: str
    resource_id: Optional[str] = ""
    action: str
    reason: str
    current_cost: float
    estimated_saving: float
    source: str  # 파일명 (aws / azure / gcp 등)
    priority: str  # HIGH / MEDIUM / LOW


class AnalyzeResponse(BaseModel):
    summary: dict
    by_cloud: dict
    by_category: dict
    suggestions: List[Suggestion]


# --------------------------------------
# 유틸 함수들
# --------------------------------------
def _infer_cloud_from_filename(filename: str) -> str:
    name = filename.lower()
    if "aws" in name:
        return "AWS"
    if "azure" in name:
        return "Azure"
    if "gcp" in name or "google" in name:
        return "Google Cloud"
    return "Unknown"


def _infer_category(service: str) -> str:
    s = (service or "").lower()
    # 아주 러프한 매핑 (PoC 용)
    if any(k in s for k in ["ec2", "vm", "compute", "gce", "virtual machine"]):
        return "COMPUTE"
    if any(k in s for k in ["s3", "storage", "blob", "disk", "ebs"]):
        return "STORAGE"
    if any(k in s for k in ["rds", "sql", "database", "db"]):
        return "DB"
    return "OTHER"


def _find_cost_column(df: pd.DataFrame) -> str:
    candidates = ["cost", "Cost", "UnblendedCost", "unblended_cost", "Amount"]
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError("비용(cost) 컬럼을 찾을 수 없습니다. CSV 컬럼명을 확인해주세요.")


def _safe_float(x) -> float:
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return 0.0
        return float(x)
    except (ValueError, TypeError):
        return 0.0


# --------------------------------------
# 핵심: 절감 규칙 적용 함수
# --------------------------------------
def apply_rules(df: pd.DataFrame) -> List[Suggestion]:
    suggestions: List[Suggestion] = []

    # 1) 저활용 컴퓨트 다운사이징 (R1)
    if {"category", "cpu_avg", "days", "cost"}.issubset(df.columns):
        mask = (df["category"] == "COMPUTE") & (df["cpu_avg"] < 3) & (df["days"] >= 7)

        for _, row in df[mask].iterrows():
            current_cost = _safe_float(row.get("cost"))
            saving = current_cost * 0.4  # 한 단계 다운사이징 가정

            suggestions.append(
                Suggestion(
                    cloud=row.get("cloud", "Unknown"),
                    category=row.get("category", "COMPUTE"),
                    service=row.get("service", "Unknown"),
                    resource_id=str(row.get("resource_id", "")),
                    action="다운사이징 추천",
                    reason="CPU 사용률 3% 미만이 7일 이상 유지되는 인스턴스입니다.",
                    current_cost=current_cost,
                    estimated_saving=saving,
                    source=str(row.get("source", "")),
                    priority="HIGH" if saving >= 30 else "MEDIUM",
                )
            )

    # 2) 미사용 스토리지 삭제 (R2)
    if {"category", "storage_idle_days", "cost"}.issubset(df.columns):
        mask = (df["category"] == "STORAGE") & (df["storage_idle_days"] >= 30)

        for _, row in df[mask].iterrows():
            current_cost = _safe_float(row.get("cost"))
            saving = current_cost  # 삭제하면 전액 절감

            suggestions.append(
                Suggestion(
                    cloud=row.get("cloud", "Unknown"),
                    category=row.get("category", "STORAGE"),
                    service=row.get("service", "Unknown"),
                    resource_id=str(row.get("resource_id", "")),
                    action="미사용 스토리지 삭제",
                    reason="30일 이상 접근 이력이 없는 스토리지입니다.",
                    current_cost=current_cost,
                    estimated_saving=saving,
                    source=str(row.get("source", "")),
                    priority="HIGH" if saving >= 20 else "MEDIUM",
                )
            )

    # 3) 장기 미접근 Object Storage 아카이브 (R3)
    if {"category", "storage_idle_days", "cost", "storage_class"}.issubset(df.columns):
        mask = (
            (df["category"] == "STORAGE")
            & (df["storage_class"].str.upper() == "STANDARD")
            & (df["storage_idle_days"] >= 90)
        )

        for _, row in df[mask].iterrows():
            current_cost = _safe_float(row.get("cost"))
            saving = current_cost * 0.5  # Standard → IA로 이동 가정

            suggestions.append(
                Suggestion(
                    cloud=row.get("cloud", "Unknown"),
                    category=row.get("category", "STORAGE"),
                    service=row.get("service", "Unknown"),
                    resource_id=str(row.get("resource_id", "")),
                    action="아카이브 스토리지로 이동",
                    reason="90일 이상 미접근 Standard 스토리지입니다.",
                    current_cost=current_cost,
                    estimated_saving=saving,
                    source=str(row.get("source", "")),
                    priority="MEDIUM",
                )
            )

    # 4) 일정 비용 이상 On-Demand → 할인 요금제 전환 (R4)
    if {"discount_type", "cost"}.issubset(df.columns):
        mask = (df["discount_type"].str.upper() == "ONDEMAND") & (df["cost"] >= 50)

        for _, row in df[mask].iterrows():
            current_cost = _safe_float(row.get("cost"))
            saving = current_cost * 0.3  # Savings Plan / RI 적용 가정

            suggestions.append(
                Suggestion(
                    cloud=row.get("cloud", "Unknown"),
                    category=row.get("category", "COMPUTE"),
                    service=row.get("service", "Unknown"),
                    resource_id=str(row.get("resource_id", "")),
                    action="할인 요금제(Reserved/Savings Plan) 적용",
                    reason="장기간 On-Demand로 사용 중인 리소스입니다.",
                    current_cost=current_cost,
                    estimated_saving=saving,
                    source=str(row.get("source", "")),
                    priority="HIGH",
                )
            )

    return suggestions


# --------------------------------------
# 루트 체크용
# --------------------------------------
@app.get("/")
def read_root():
    return {"message": "CloudSaver (CS) backend running"}


# --------------------------------------
# 메인 분석 엔드포인트
# --------------------------------------
@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="CSV 파일을 하나 이상 업로드해주세요.")

    frames = []

    # 1) CSV 읽기 + 공통 컬럼 정리
    for f in files:
        raw = await f.read()
        try:
            # utf-8-sig로 BOM 문제도 같이 해결
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp949")  # 혹시 모를 한글 인코딩

        df = pd.read_csv(StringIO(text))

        # cloud 컬럼 없으면 파일명 기준으로 추론
        if "cloud" not in df.columns:
            df["cloud"] = _infer_cloud_from_filename(f.filename)

        # service 컬럼 없으면 후보에서 하나 골라서 service로 매핑
        if "service" not in df.columns:
            for cand in ["Service", "ServiceName", "service_description", "MeterCategory"]:
                if cand in df.columns:
                    df["service"] = df[cand]
                    break
            else:
                df["service"] = "Unknown"

        # category 컬럼 없으면 service 기반으로 추론
        if "category" not in df.columns:
            df["category"] = df["service"].apply(_infer_category)

        # cost 컬럼 통일
        if "cost" not in df.columns:
            try:
                cost_col = _find_cost_column(df)
                df["cost"] = df[cost_col]
            except KeyError as e:
                raise HTTPException(status_code=400, detail=str(e))

        # 나머지 분석용 컬럼이 없으면 기본값 채우기
        for col, default in [
            ("cpu_avg", None),
            ("days", 7),
            ("storage_idle_days", 0),
            ("storage_class", "STANDARD"),
            ("discount_type", "OnDemand"),
            ("resource_id", ""),
        ]:
            if col not in df.columns:
                df[col] = default

        # 파일명 기록
        df["source"] = f.filename

        frames.append(df)

    # 2) 하나의 DataFrame으로 병합
    if not frames:
        raise HTTPException(status_code=400, detail="유효한 데이터가 없습니다.")

    data = pd.concat(frames, ignore_index=True)

    # 숫자형 컬럼 강제 변환 (에러는 NaN으로)
    for col in ["cost", "cpu_avg", "days", "storage_idle_days"]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

    # 3) 절감 규칙 적용
    suggestions = apply_rules(data)

    # 4) 총 비용 / 총 절감액 계산
    total_cost = float(data["cost"].sum()) if "cost" in data.columns else 0.0
    total_saving = float(sum(s.estimated_saving for s in suggestions))

    # 5) 그래프용 집계 데이터 (cloud / category 기준)
    if "cloud" in data.columns:
        by_cloud_cost = (
            data.groupby("cloud")["cost"].sum().reset_index().to_dict(orient="records")
        )
    else:
        by_cloud_cost = []

    if suggestions:
        sug_df = pd.DataFrame([s.dict() for s in suggestions])
        by_cloud_saving = (
            sug_df.groupby("cloud")["estimated_saving"]
            .sum()
            .reset_index()
            .to_dict(orient="records")
        )
        by_category_saving = (
            sug_df.groupby("category")["estimated_saving"]
            .sum()
            .reset_index()
            .to_dict(orient="records")
        )
    else:
        by_cloud_saving = []
        by_category_saving = []

    response = AnalyzeResponse(
        summary={
            "total_cost": total_cost,
            "total_saving": total_saving,
            "saving_rate": (total_saving / total_cost * 100) if total_cost > 0 else 0.0,
        },
        by_cloud={
            "cost": by_cloud_cost,
            "saving": by_cloud_saving,
        },
        by_category={
            "saving": by_category_saving,
        },
        suggestions=suggestions,
    )

    return response

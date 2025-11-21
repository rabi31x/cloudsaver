from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from io import StringIO
from starlette.responses import StreamingResponse
from fpdf import FPDF # 👈 FPDF 라이브러리 임포트 추가

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
allow_origins=["http://localhost:3000"], # React 개발 서버
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)


# --------------------------------------
# Pydantic 모델 (응답 스키마)
# --------------------------------------
class Suggestion(BaseModel):
# ... (Suggestion 클래스 정의는 유지)
    cloud: str
    category: str
    service: str
    resource_id: Optional[str] = ""
    action: str
    reason: str
    current_cost: float
    estimated_saving: float
    source: str # 파일명 (aws / azure / gcp 등)
    priority: str # HIGH / MEDIUM / LOW


class AnalyzeResponse(BaseModel):
# ... (AnalyzeResponse 클래스 정의는 유지)
    summary: dict
    by_cloud: dict
    by_category: dict
    suggestions: List[Suggestion]


# --------------------------------------
# 유틸 함수들
# ... (_infer_cloud_from_filename, _infer_category, _find_cost_column, _safe_float 함수는 유지)
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
# ... (apply_rules 함수는 유지)
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
# ... (analyze 함수 내용은 유지)
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


# --------------------------------------
# PDF 생성 로직
# --------------------------------------
# main.py 파일 내 create_pdf_report 함수 수정 (전체)

def create_pdf_report(suggestions: List[Suggestion], summary: dict) -> bytes:
    """분석 결과를 기반으로 간단한 PDF 보고서를 생성합니다."""
    # FPDF 객체 생성
    pdf = FPDF()

    # NanumGothic 폰트 등록
    try:
        pdf.add_font('NanumGothic', '', 'NanumGothic.ttf', uni=True)
        pdf.add_font('NanumGothic', 'B', 'NanumGothicBold.ttf', uni=True) 
        
        # 폰트 등록 성공 시, NanumGothic으로 강제 설정
        pdf.set_font('NanumGothic', '', 10) 
        
    except RuntimeError:
        print("경고: NanumGothic 폰트 파일 등록에 실패했습니다. 기본 Arial 폰트로 대체합니다.")
        # 폰트 등록 실패 시, Arial 폰트로 강제 설정 (한글 깨짐 감수)
        pdf.set_font("Arial", "", 10)

    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # ------------------------------------
    # 제목
    pdf.set_font("NanumGothic", "B", 16) 
    pdf.cell(0, 10, "CloudSaver 비용 절감 보고서", 0, 1, "C") 
    pdf.ln(5)

    # 1. 요약 정보
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("NanumGothic", "B", 12)
    pdf.cell(0, 8, "1. Summary", 0, 1, 'L', 1)
    
    pdf.set_font("NanumGothic", "", 10) # 레귤러 스타일
    pdf.cell(0, 6, f"Total Cost: ${summary.get('total_cost', 0):,.0f}", 0, 1)
    pdf.cell(0, 6, f"Total Estimated Saving: ${summary.get('total_saving', 0):,.0f}", 0, 1)
    pdf.cell(0, 6, f"Saving Rate: {summary.get('saving_rate', 0):.1f}%", 0, 1)
    pdf.ln(5)

    # 2. 상세 제안
    pdf.set_font("NanumGothic", "B", 12)
    pdf.cell(0, 8, f"2. Detailed Suggestions ({len(suggestions)} items)", 0, 1, 'L', 1)
    
    pdf.set_font("NanumGothic", "", 9) # 레귤러 스타일로 복귀
    col_widths = [15, 30, 30, 25, 25, 55]
    
    # 테이블 헤더
    headers = ["Cloud", "Service", "Action", "Saving ($)", "Current Cost ($)", "Reason"]
    pdf.set_fill_color(200, 220, 255) 
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 7, header, 1, 0, "C", 1)
    pdf.ln()

    # 데이터 행
    pdf.set_fill_color(255, 255, 255)
    
    for s in suggestions:
        # 1. MultiCell을 위한 초기 위치 저장
        start_x = pdf.get_x()
        start_y = pdf.get_y()
        
        # 2. Reason 필드만 먼저 MultiCell로 출력하여 셀 높이 결정
        # Border는 0으로 지정하여 일단 테두리를 그리지 않고 높이만 측정합니다.
        pdf.set_xy(start_x + sum(col_widths[:-1]), start_y)
        pdf.multi_cell(col_widths[-1], 7, s.reason, 0, "L", 0)
        
        # 3. MultiCell의 실제 높이를 계산
        end_y = pdf.get_y()
        cell_height = end_y - start_y
        
        # 4. 커서 위치를 행 시작점(start_x, start_y)으로 복귀
        pdf.set_xy(start_x, start_y)
        
        # 5. 모든 셀을 행의 높이(cell_height)에 맞추어 출력 (내용+테두리 한 번에)
        
        # Reason 열을 제외한 5개 열 (Cell)
        pdf.cell(col_widths[0], cell_height, s.cloud, 1, 0, "L", 0)
        pdf.cell(col_widths[1], cell_height, s.service, 1, 0, "L", 0)
        pdf.cell(col_widths[2], cell_height, s.action, 1, 0, "L", 0)
        pdf.cell(col_widths[3], cell_height, f"{s.estimated_saving:.2f}", 1, 0, "R", 0)
        pdf.cell(col_widths[4], cell_height, f"{s.current_cost:.2f}", 1, 0, "R", 0)
        
        # 6. Reason 셀 (MultiCell)을 텍스트와 테두리를 함께 출력하고, 다음 줄로 자동 이동(ln=1)
        # Reason 텍스트와 테두리를 한 번에 출력 (가장 안정적인 방식)
        # 주의: MultiCell은 출력이 끝나면 Y축만 이동하므로 X축을 초기화해야 합니다.
        pdf.multi_cell(col_widths[-1], 7, s.reason, 1, "L", 0)
        
        # 🚨🚨🚨 이 줄이 없으면 다음 행이 잘못된 X 위치에서 시작됩니다. 🚨🚨🚨
        # X축을 다음 행 시작점(start_x)으로 명확하게 초기화
        pdf.set_x(start_x)

    return pdf.output(dest='S')

# --------------------------------------
# 리포트 다운로드 엔드포인트 (수정됨)
# --------------------------------------

@app.post("/download_report")
async def download_report(data: AnalyzeResponse, format: str = "csv"): # 👈 format 파라미터 추가
    """
    분석 결과를 받아 지정된 포맷(csv 또는 pdf)으로 반환합니다.
    """
    if not data.suggestions:
        raise HTTPException(status_code=404, detail="다운로드할 절감 제안 데이터가 없습니다.")

    # 1. PDF 포맷 요청 처리
    if format.lower() == "pdf":
        try:
            pdf_bytes = create_pdf_report(data.suggestions, data.summary)
            
            return StreamingResponse(
                iter([pdf_bytes]),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": "attachment; filename=cloudsaver_report.pdf"
                }
            )
        except Exception as e:
            # FPDF 에러 발생 시 처리
            print(f"PDF 생성 오류: {e}")
            raise HTTPException(status_code=500, detail=f"PDF 생성 중 오류가 발생했습니다. (폰트 문제일 수 있음): {e}")

    # 2. CSV 포맷 요청 처리 (기존 로직)
    elif format.lower() == "csv":
        suggestions_data = [s.dict() for s in data.suggestions]

        df = pd.DataFrame(suggestions_data)

        # 필요한 컬럼만 선택하고 순서 변경 (가독성 향상)
        columns_order = [
            "cloud", 
            "service", 
            "action", 
            "priority", 
            "estimated_saving", 
            "current_cost", 
            "reason", 
            "source"
        ]
        df = df[columns_order]

        # 컬럼 이름 한글로 변경
        df.rename(columns={
            "cloud": "클라우드",
            "service": "서비스",
            "action": "제안 액션",
            "priority": "우선순위",
            "estimated_saving": "예상 절감액 ($)",
            "current_cost": "현재 비용 ($)",
            "reason": "제안 이유",
            "source": "원본 파일"
        }, inplace=True)
        
        # CSV 문자열 생성
        csv_stream = StringIO()
        df.to_csv(csv_stream, index=False, encoding='utf-8-sig') 
        
        csv_stream.seek(0)
        
        # 스트리밍 응답으로 CSV 파일 반환
        return StreamingResponse(
            iter([csv_stream.read()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=cloudsaver_report.csv"
            }
        )

    # 3. 지원하지 않는 포맷 요청 처리
    else:
        raise HTTPException(status_code=400, detail="지원하지 않는 포맷입니다. (csv 또는 pdf를 사용하세요.)")
        
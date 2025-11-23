from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from io import StringIO, BytesIO
from starlette.responses import StreamingResponse

import pandas as pd
import math

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm

app = FastAPI(
    title="CloudSaver (CS) Backend",
    description="멀티 클라우드 비용 CSV를 분석해서 절감 제안을 반환하는 API",
    version="0.1.0",
)

# 프론트엔드 도메인 허용 (개발용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic 모델 (응답 스키마)
class Suggestion(BaseModel):
    cloud: str
    category: str
    service: str
    resource_id: Optional[str] = ""
    action: str
    reason: str
    current_cost: float
    estimated_saving: float
    source: str  # 파일명 (aws / azure / gcp)
    priority: str


class AnalyzeResponse(BaseModel):
    summary: Dict[str, Any]
    by_cloud: Dict[str, Any]
    by_category: Dict[str, Any]
    suggestions: List[Suggestion]



# 유틸 함수
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



# 절감 규칙 적용 함수
def apply_rules(df: pd.DataFrame) -> List[Suggestion]:
    suggestions: List[Suggestion] = []

    # 저활용 컴퓨트 다운사이징 (R1)
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

    # 미사용 스토리지 삭제 (R2)
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

    # 장기 미접근 Object Storage 아카이브 (R3)
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

    # 일정 비용 이상 On-Demand → 할인 요금제 전환 (R4)
    if {"discount_type", "cost"}.issubset(df.columns):
        # discount_type이 NaN이면 str.upper()에서 에러 나므로 fillna 처리
        df["discount_type"] = df["discount_type"].fillna("")
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


# 루트 체크용
@app.get("/")
def read_root():
    return {"message": "CloudSaver (CS) backend running"}


# 메인 분석 엔드포인트
@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="CSV 파일을 하나 이상 업로드해주세요.")

    frames = []

    # 1) CSV 읽기 + 공통 컬럼 정리
    for f in files:
        raw = await f.read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp949")  # 한글 인코딩 대응

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

    # 숫자형 컬럼 강제 변환 (에러는 NaN → 0)
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


# PDF 생성 로직
def create_pdf_report(suggestions: List[Suggestion], summary: dict) -> bytes:
    """ReportLab로 CloudSaver 기본형 PDF 보고서 생성"""
    buffer = BytesIO()

    # 문서 기본 설정 (A4, 여백)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    # ---------------- 폰트 설정 ----------------
    # 기본값
    base_font = "Helvetica"

    try:
        pdfmetrics.registerFont(TTFont("NanumGothic", "NanumGothic.ttf"))
        pdfmetrics.registerFont(TTFont("NanumGothic-Bold", "NanumGothicBold.ttf"))
        base_font = "NanumGothic"
    except Exception as e:
        print(f"경고: 나눔고딕 등록 실패, 기본 폰트 사용: {e}")

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TitleK",
        parent=styles["Title"],
        fontName=base_font,
        fontSize=16,
        leading=20,
        alignment=1,
        spaceAfter=12,
    )

    section_title_style = ParagraphStyle(
        "SectionTitleK",
        parent=styles["Heading2"],
        fontName=base_font,
        fontSize=11,
        leading=14,
        spaceBefore=6,
        spaceAfter=6,
    )

    normal_style = ParagraphStyle(
        "NormalK",
        parent=styles["Normal"],
        fontName=base_font,
        fontSize=9,
        leading=11,
    )

    header_style = ParagraphStyle(
        "HeaderK",
        parent=styles["Normal"],
        fontName=base_font,
        fontSize=9,
        leading=11,
        alignment=1, 
    )

    elements = []

    # ---------------- 제목 ----------------
    elements.append(Paragraph("CloudSaver 비용 절감 보고서", title_style))
    elements.append(Spacer(1, 6))

    # ---------------- 1. Summary ----------------
    elements.append(Paragraph("1. Summary", section_title_style))
    elements.append(
        Paragraph(
            f"Total Cost: ${summary.get('total_cost', 0):,.0f}",
            normal_style,
        )
    )
    elements.append(
        Paragraph(
            f"Total Estimated Saving: ${summary.get('total_saving', 0):,.0f}",
            normal_style,
        )
    )
    elements.append(
        Paragraph(
            f"Saving Rate: {summary.get('saving_rate', 0):.1f}%",
            normal_style,
        )
    )
    elements.append(Spacer(1, 10))

    # ---------------- 2. Detailed Suggestions ----------------
    elements.append(
        Paragraph(
            f"2. Detailed Suggestions ({len(suggestions)} items)",
            section_title_style,
        )
    )
    elements.append(Spacer(1, 4))

    # 표 데이터 구성
    table_data = []

    # 헤더
    headers = ["Cloud", "Service", "Action", "Saving ($)", "Current Cost ($)", "Reason"]
    table_data.append([Paragraph(h, header_style) for h in headers])

    # 행 데이터
    for s in suggestions:
        row = [
            Paragraph(str(s.cloud), normal_style),
            Paragraph(str(s.service), normal_style),
            Paragraph(str(s.action), normal_style),
            Paragraph(f"{s.estimated_saving:.2f}", normal_style),
            Paragraph(f"{s.current_cost:.2f}", normal_style),
            Paragraph(str(s.reason), normal_style),
        ]
        table_data.append(row)

    # 컬럼 너비 설정
    total_width = doc.width
    col_widths = [
        20 * mm,   # Cloud
        25 * mm,   # Service
        40 * mm,   # Action
        22 * mm,   # Saving
        25 * mm,   # Current Cost
        total_width - (20 + 25 + 40 + 22 + 25) * mm,
    ]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    # 표 스타일
    table.setStyle(
        TableStyle(
            [
                # 전체 폰트
                ("FONTNAME", (0, 0), (-1, -1), base_font),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),

                # 헤더 스타일
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c8ddff")),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),

                # 숫자 오른쪽 정렬
                ("ALIGN", (3, 1), (4, -1), "RIGHT"),

                # 그리드 라인
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),

                # 행 간 약간 여백
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    elements.append(table)

    # PDF 빌드
    doc.build(elements)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes



# 리포트 다운로드 엔드포인트
@app.post("/download_report")
async def download_report(data: AnalyzeResponse, format: str = "csv"):
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
                BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=cloudsaver_report.pdf"},  
            )

        except Exception as e:
            print(f"PDF 생성 오류: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"PDF 생성 중 오류가 발생했습니다. (폰트 문제일 수 있음): {e}",
            )

    # 2. CSV 포맷 요청 처리
    elif format.lower() == "csv":
        suggestions_data = [s.dict() for s in data.suggestions]
        df = pd.DataFrame(suggestions_data)

        columns_order = [
            "cloud",
            "service",
            "action",
            "priority",
            "estimated_saving",
            "current_cost",
            "reason",
            "source",
        ]
        df = df[columns_order]

        df.rename(
            columns={
                "cloud": "클라우드",
                "service": "서비스",
                "action": "제안 액션",
                "priority": "우선순위",
                "estimated_saving": "예상 절감액 ($)",
                "current_cost": "현재 비용 ($)",
                "reason": "제안 이유",
                "source": "원본 파일",
            },
            inplace=True,
        )

        csv_stream = StringIO()
        df.to_csv(csv_stream, index=False, encoding="utf-8-sig")
        csv_stream.seek(0)

        return StreamingResponse(
            iter([csv_stream.read()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=cloudsaver_report.csv"
            },
        )

    # 3. 지원하지 않는 포맷 요청 처리
    else:
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 포맷입니다. (csv 또는 pdf를 사용하세요.)",
        )

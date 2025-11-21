// src/pages/DashboardView.jsx
import React, { useState, useMemo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
} from "recharts";
import * as S from "../styles/dashboardViewStyles"; 

const CLOUD_TABS = [
  { id: "ALL", label: "All Cloud" },
  { id: "AWS", label: "AWS" },
  { id: "Azure", label: "Azure" },
  { id: "Google Cloud", label: "Google Cloud" },
];

const CLOUD_COLORS = ["#4B5563", "#9CA3AF", "#D1D5DB"];

function EmptyChart() {
  return (
    <div style={S.emptyChartStyle}>
      표시할 데이터가 없습니다.
    </div>
  );
}

export default function DashboardView({ data, onNew }) {
  const [activeCloud, setActiveCloud] = useState("ALL");
  const [showDropdown, setShowDropdown] = useState(false); // ✨ 드롭다운 상태 추가

  const cloudCostData = useMemo(() => {
    if (!data?.by_cloud?.cost) return [];
    return data.by_cloud.cost.map((row) => ({
      name: row.cloud,
      value: row.cost,
    }));
  }, [data]);

  const cloudSavingData = useMemo(() => {
    if (!data?.by_cloud?.saving) return [];
    return data.by_cloud.saving.map((row) => ({
      name: row.cloud,
      saving: row.estimated_saving,
    }));
  }, [data]);

  const suggestions = useMemo(() => {
    if (!data?.suggestions) return [];
    if (activeCloud === "ALL") return data.suggestions;
    return data.suggestions.filter((s) => s.cloud === activeCloud);
  }, [data, activeCloud]);

  const { total_cost = 0, total_saving = 0, saving_rate = 0 } =
    data?.summary || {};

  // ✨ handleDownloadReport 함수를 format을 받도록 수정
  // src/pages/DashboardView.jsx (handleDownloadReport 함수 전체)

const handleDownloadReport = async (format) => {
    setShowDropdown(false); // 드롭다운 닫기

    try {
      // 1. 백엔드의 다운로드 엔드포인트 호출 (format 파라미터 사용)
      const res = await fetch(`http://localhost:8000/download_report?format=${format}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "리포트 다운로드 API 호출에 실패했습니다.");
      }

      // 2. 응답 받은 Blob을 다운로드
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);

      // 3. 파일명 설정: format에 따라 확장자 지정
      const filename = `cloudsaver_report.${format}`; 

      const a = document.createElement("a");
      a.href = url;
      a.download = filename; // 파일명 설정
      a.click();
      URL.revokeObjectURL(url);

    } catch (error) {
      console.error("다운로드 중 오류 발생:", error);
      alert(`리포트 다운로드에 실패했습니다: ${error.message}`);
    }
};
  
  return (
    <div style={S.container}>
      {/* 상단 요약 + 버튼 */}
      <div style={S.headerRow}>
        <div>
          <h2 style={S.titleStyle}>Cloud list</h2>
          <div style={S.subtitleStyle}>
            총 비용{" "}
            <strong>
              ${total_cost.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </strong>{" "}
            중{" "}
            <strong>
              ${total_saving.toLocaleString(undefined, {
                maximumFractionDigits: 0,
              })}
            </strong>{" "}
            (약 {saving_rate.toFixed(1)}%) 절감 가능
          </div>
        </div>

        <div style={S.buttonGroupStyle}>
          {/* ✨ 드롭다운 컨테이너 추가 */}
          <div style={S.dropdownContainer}> 
            <button 
              type="button" 
              onClick={() => setShowDropdown(!showDropdown)} 
              style={S.pillButton}
            >
              Report Download ⬇️
            </button>
            
            {showDropdown && (
              <div style={S.dropdownMenu}>
                <button onClick={() => handleDownloadReport('csv')} style={S.dropdownItem}>
                  Download as CSV
                </button>
                <button onClick={() => handleDownloadReport('pdf')} style={S.dropdownItem}>
                  Download as PDF
                </button>
              </div>
            )}
          </div>
          {/* ✨ 드롭다운 관련 끝 */}

          <button type="button" style={S.pillButton}>
            Save
          </button>
          <button type="button" style={S.pillButton} onClick={onNew}>
            ＋ NEW
          </button>
        </div>
      </div>

      {/* 2컬럼 레이아웃 */}
      <div style={S.mainRow}>
        {/* 왼쪽: 탭 + 솔루션 카드 */}
        <div style={S.leftPane}>
          <div style={S.cloudTabs}>
            {CLOUD_TABS.map((c) => {
              const active = c.id === activeCloud;
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setActiveCloud(c.id)}
                  style={{
                    ...S.cloudTabButton,
                    ...(active ? S.cloudTabActive : {}),
                  }}
                >
                  {c.label}
                </button>
              );
            })}
          </div>

          <div style={S.solutionBox}>
            {suggestions.length === 0 && (
              <div style={S.emptySolutionStyle}>
                아직 표시할 절감 제안이 없습니다.
              </div>
            )}

            {suggestions.map((s, idx) => (
              <div
                key={`${s.resource_id}-${idx}`}
                style={{
                  ...S.solutionCard,
                  // 우선순위에 따른 border-left 스타일 로직은 그대로 유지
                  borderLeft:
                    s.priority === "HIGH"
                      ? "3px solid #ef4444"
                      : s.priority === "MEDIUM"
                      ? "3px solid #f59e0b"
                      : "3px solid #9ca3af",
                }}
              >
                <div style={S.cardHeaderStyle}>
                  <div style={S.cardTitleStyle}>
                    [{s.cloud}] {s.service} – {s.action}
                  </div>
                  <div style={S.categoryBadgeStyle}>
                    {s.category}
                  </div>
                </div>
                <div style={S.cardReasonStyle}>
                  {s.reason}
                </div>
                <div style={S.cardCostStyle}>
                  현재 비용: ${s.current_cost.toFixed(2)} / 예상 절감액:{" "}
                  <strong>${s.estimated_saving.toFixed(2)}</strong>
                </div>
                {s.source && (
                  <div style={S.cardSourceStyle}>
                    source: {s.source}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 오른쪽: 차트들 */}
        <div style={S.rightPane}>
          <div style={S.chartCard}>
            <div style={S.chartTitleStyle}>
              Cloud 비용 분포
            </div>
            {cloudCostData.length === 0 ? (
              <EmptyChart />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={cloudCostData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={2}
                  >
                    {cloudCostData.map((entry, index) => (
                      <Cell
                        key={`slice-${index}`}
                        fill={CLOUD_COLORS[index % CLOUD_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>

          <div style={S.chartCard}>
            <div style={S.chartTitleStyle}>
              Cloud별 예상 절감액
            </div>
            {cloudSavingData.length === 0 ? (
              <EmptyChart />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={cloudSavingData}>
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="saving" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
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

const CLOUD_TABS = [
  { id: "ALL", label: "All Cloud" },
  { id: "AWS", label: "AWS" },
  { id: "Azure", label: "Azure" },
  { id: "Google Cloud", label: "Google Cloud" },
];

const CLOUD_COLORS = ["#4B5563", "#9CA3AF", "#D1D5DB"];

const pillButtonStyle = {
  padding: "8px 18px",
  borderRadius: 999,
  border: "none",
  backgroundColor: "#ffffff",
  boxShadow: "0 3px 10px rgba(0,0,0,0.06)",
  cursor: "pointer",
  fontSize: 13,
  fontWeight: 600,
};

function EmptyChart() {
  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "#d1d5db",
        fontSize: 13,
      }}
    >
      표시할 데이터가 없습니다.
    </div>
  );
}

export default function DashboardView({ data, onNew }) {
  const [activeCloud, setActiveCloud] = useState("ALL");

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

  const handleDownloadReport = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "cloudsaver_report.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      style={{
        width: "90%",
        maxWidth: 1200,
        backgroundColor: "#ffffff",
        borderRadius: 16,
        boxShadow: "0 10px 30px rgba(0,0,0,0.06)",
        padding: 24,
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      {/* 상단 요약 + 버튼 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 8,
        }}
      >
        <div>
          <h2 style={{ fontSize: 26, marginBottom: 4 }}>Cloud list</h2>
          <div style={{ fontSize: 13, color: "#6b7280" }}>
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

        <div style={{ display: "flex", gap: 12 }}>
          <button type="button" onClick={handleDownloadReport} style={pillButtonStyle}>
            Report Download
          </button>
          <button type="button" style={pillButtonStyle}>
            Save
          </button>
          <button type="button" style={pillButtonStyle} onClick={onNew}>
            ＋ NEW
          </button>
        </div>
      </div>

      {/* 2컬럼 레이아웃 */}
      <div style={{ display: "flex", gap: 24, minHeight: 420 }}>
        {/* 왼쪽: 탭 + 솔루션 카드 */}
        <div style={{ flex: 1.1, display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
            {CLOUD_TABS.map((c) => {
              const active = c.id === activeCloud;
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setActiveCloud(c.id)}
                  style={{
                    flex: 1,
                    borderRadius: 12,
                    border: active ? "2px solid #2E6CCF" : "1px solid #d1d5db",
                    padding: "8px 12px",
                    backgroundColor: active ? "#eff6ff" : "#ffffff",
                    cursor: "pointer",
                    fontSize: 13,
                    fontWeight: 500,
                  }}
                >
                  {c.label}
                </button>
              );
            })}
          </div>

          <div
            style={{
              flex: 1,
              backgroundColor: "#f9fafb",
              borderRadius: 14,
              padding: 16,
              overflowY: "auto",
            }}
          >
            {suggestions.length === 0 && (
              <div
                style={{
                  height: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#9ca3af",
                  fontSize: 14,
                }}
              >
                아직 표시할 절감 제안이 없습니다.
              </div>
            )}

            {suggestions.map((s, idx) => (
              <div
                key={`${s.resource_id}-${idx}`}
                style={{
                  backgroundColor: "#ffffff",
                  borderRadius: 12,
                  padding: 12,
                  marginBottom: 10,
                  boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
                  borderLeft:
                    s.priority === "HIGH"
                      ? "3px solid #ef4444"
                      : s.priority === "MEDIUM"
                      ? "3px solid #f59e0b"
                      : "3px solid #9ca3af",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 4,
                    alignItems: "center",
                  }}
                >
                  <div style={{ fontWeight: 600 }}>
                    [{s.cloud}] {s.service} – {s.action}
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      padding: "2px 8px",
                      borderRadius: 999,
                      backgroundColor: "#eef2ff",
                      color: "#4f46e5",
                    }}
                  >
                    {s.category}
                  </div>
                </div>
                <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 4 }}>
                  {s.reason}
                </div>
                <div style={{ fontSize: 12, color: "#9ca3af" }}>
                  현재 비용: ${s.current_cost.toFixed(2)} / 예상 절감액:{" "}
                  <strong>${s.estimated_saving.toFixed(2)}</strong>
                </div>
                {s.source && (
                  <div style={{ fontSize: 11, color: "#d1d5db", marginTop: 2 }}>
                    source: {s.source}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 오른쪽: 차트들 */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              backgroundColor: "#ffffff",
              borderRadius: 14,
              border: "1px solid #e5e7eb",
              padding: 16,
              height: 220,
            }}
          >
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>
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

          <div
            style={{
              backgroundColor: "#ffffff",
              borderRadius: 14,
              border: "1px solid #e5e7eb",
              padding: 16,
              height: 220,
            }}
          >
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>
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

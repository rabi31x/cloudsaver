import React, { useState } from "react";

const CLOUDS = [
  { id: "aws", label: "AWS" },
  { id: "azure", label: "Azure" },
  { id: "gcp", label: "Google Cloud" },
];

export default function UploadView({ onAnalyzeSuccess }) {
  const [selectedCloud, setSelectedCloud] = useState("aws");
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
    setError("");
  };

  const handleAnalyze = async () => {
    if (files.length === 0) {
      setError("CSV 파일을 하나 이상 선택해주세요.");
      return;
    }

    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    setLoading(true);
    setError("");

    try {
      const res = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "분석 API 호출에 실패했습니다.");
      }

      const data = await res.json();
      onAnalyzeSuccess(data);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        width: 720,
        backgroundColor: "#ffffff",
        borderRadius: 16,
        boxShadow: "0 10px 30px rgba(0,0,0,0.06)",
        padding: 32,
      }}
    >
      <h2 style={{ fontSize: 28, marginBottom: 24 }}>Cloud Select</h2>

      {/* 클라우드 선택 탭 */}
      <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
        {CLOUDS.map((c) => {
          const active = c.id === selectedCloud;
          return (
            <button
              key={c.id}
              type="button"
              onClick={() => setSelectedCloud(c.id)}
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                borderRadius: 12,
                border: active ? "2px solid #2E6CCF" : "1px solid #d1d5db",
                backgroundColor: active ? "#eff6ff" : "#ffffff",
                padding: "10px 16px",
                cursor: "pointer",
                fontWeight: 500,
              }}
            >
              <span style={{ fontSize: 13, textTransform: "uppercase" }}>
                {c.id}
              </span>
              <span>{c.label}</span>
            </button>
          );
        })}
      </div>

      {/* 업로드 박스 */}
      <div
        style={{
          borderRadius: 16,
          backgroundColor: "#f3f4f6",
          border: "1px dashed #d1d5db",
          height: 260,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 16,
        }}
      >
        <div style={{ fontSize: 40 }}>＋</div>
        <div style={{ fontSize: 16, fontWeight: 500 }}>Upload</div>
        <input
          type="file"
          accept=".csv"
          multiple
          onChange={handleFileChange}
          style={{ marginTop: 8 }}
        />
        <div style={{ fontSize: 12, color: "#9ca3af" }}>
          {selectedCloud.toUpperCase()} 비용 리포트 CSV를 선택하세요 (여러 개 가능)
        </div>
      </div>

      {files.length > 0 && (
        <div style={{ marginTop: 16, fontSize: 13 }}>
          <strong>선택된 파일:</strong>{" "}
          {files.map((f) => f.name).join(", ")}
        </div>
      )}

      {error && (
        <div style={{ marginTop: 12, color: "#ef4444", fontSize: 13 }}>
          {error}
        </div>
      )}

      <div style={{ marginTop: 24, textAlign: "right" }}>
        <button
          type="button"
          onClick={handleAnalyze}
          disabled={loading}
          style={{
            padding: "10px 20px",
            borderRadius: 999,
            border: "none",
            backgroundColor: loading ? "#9ca3af" : "#2E6CCF",
            color: "#ffffff",
            fontWeight: 600,
            cursor: loading ? "default" : "pointer",
            boxShadow: "0 4px 10px rgba(46,108,207,0.3)",
          }}
        >
          {loading ? "분석 중..." : "분석하기"}
        </button>
      </div>
    </div>
  );
}

// src/pages/UploadView.jsx
import React, { useState, useRef } from "react";
import * as S from "../styles/uploadViewStyles";

const CLOUDS = [
  { id: "aws", label: "AWS" },
  { id: "azure", label: "Azure" },
  { id: "gcp", label: "Google Cloud" },
];

export default function UploadView({ onAnalyzeSuccess }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef(null);

  const handleFiles = (fileList) => {
    const arr = Array.from(fileList);
    // CSV만 필터링
    const csvFiles = arr.filter(
      (f) => f.type === "text/csv" || f.name.toLowerCase().endsWith(".csv")
    );
    if (csvFiles.length === 0) {
      setError("CSV 파일을 업로드해주세요.");
      return;
    }
    setFiles(csvFiles);
    setError("");
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
      e.dataTransfer.clearData();
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  const handleAnalyze = async () => {
    if (files.length === 0) {
      setError("클라우드 비용 리포트 CSV 파일을 먼저 업로드해주세요.");
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
    <div style={S.container}>
      {/* 제목 & 설명 */}
      <h2 style={S.title}>Cloud list</h2>
      <div style={S.subtitle}>
        분석이 가능한 클라우드 리스트입니다. 사용 중인 클라우드를 선택할 필요 없이,
        클라우드 비용 리포트 CSV 파일을 업로드해 절감 가능성을 확인하세요.
      </div>

      {/* 클라우드 리스트 UI (기능 없이 div로만 표시) */}
      <div style={S.cloudTabs}>
        {CLOUDS.map((c) => (
          <div
            key={c.id}
            style={S.cloudButton}
          >
            <span style={{ fontSize: 13, textTransform: "uppercase" }}>
              {c.id.toUpperCase()}
            </span>
            <span>{c.label}</span>
          </div>
        ))}
      </div>

      {/* 업로드 박스 (클릭 + 드래그 앤 드롭) */}
      <div
        style={{
          ...S.uploadBox,
          ...(isDragging ? S.uploadBoxActive : {}),
        }}
        onClick={openFileDialog}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <div style={S.uploadIcon}>＋</div>
        <div style={S.uploadTitle}>Upload</div>
        <div style={S.uploadHint}>
          클라우드 비용 리포트 CSV 파일을 업로드해주세요.
          <br />
          파일 선택 버튼을 누르거나, 이 영역으로 드래그 앤 드롭할 수 있습니다.
        </div>

        {/* 실제 input은 숨겨두고 ref로 제어 */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          multiple
          onChange={handleFileChange}
          style={{ display: "none" }}
        />

        {/* 보조용 파일 선택 버튼 */}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            openFileDialog();
          }}
          style={{
            marginTop: 12,
            padding: "6px 14px",
            borderRadius: 999,
            border: "1px solid #d1d5db",
            backgroundColor: "#ffffff",
            fontSize: 12,
            cursor: "pointer",
          }}
        >
          파일 선택
        </button>
      </div>

      {files.length > 0 && (
        <div style={S.fileListText}>
          <strong>선택된 파일:</strong> {files.map((f) => f.name).join(", ")}
        </div>
      )}

      {error && <div style={S.errorText}>{error}</div>}

      <div style={{ marginTop: 24, textAlign: "right" }}>
        <button
          type="button"
          onClick={handleAnalyze}
          disabled={loading}
          style={S.analyzeButton(loading)}
        >
          {loading ? "분석 중..." : "분석하기"}
        </button>
      </div>
    </div>
  );
}

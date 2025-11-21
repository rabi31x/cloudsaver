import React, { useState } from "react";

export default function UploadAnalyzer() {
  const [files, setFiles] = useState([]);
  const [result, setResult] = useState(null);

  const handleUpload = async () => {
    const formData = new FormData();

    // 파일 여러 개 append
    Array.from(files).forEach((file) => {
      formData.append("files", file);
    });

    const response = await fetch("http://localhost:8000/analyze", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    setResult(data);
  };

  return (
    <div style={{ padding: "20px" }}>
      <h2>CloudSaver CSV 분석</h2>

      <input
        type="file"
        multiple
        onChange={(e) => setFiles(e.target.files)}
      />

      <button onClick={handleUpload}>분석 요청</button>

      {result && (
        <div style={{ marginTop: "20px" }}>
          <h3>분석 결과</h3>
          <p>총 절감액: {result.total_saving} USD</p>
          <p>제안 개수: {result.count}</p>

          {result.suggestions.map((s, index) => (
            <div key={index} style={{ border: "1px solid #ddd", padding: "10px", marginBottom: "10px" }}>
              <strong>{s.service}</strong>  
              <div>조치: {s.action}</div>
              <div>절감액: {s.estimated_saving}</div>
              <div>근거: {s.reason}</div>
              <div>출처: {s.source}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

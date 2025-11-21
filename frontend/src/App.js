import React, { useState } from "react";
import UploadView from "./pages/UploadView";
import DashboardView from "./pages/DashboardView";

function App() {
  const [step, setStep] = useState("upload"); // 'upload' | 'dashboard'
  const [apiResult, setApiResult] = useState(null);

  const handleAnalyzeSuccess = (data) => {
    setApiResult(data);
    setStep("dashboard");
  };

  const handleNewAnalysis = () => {
    setApiResult(null);
    setStep("upload");
  };

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#f7f7f7" }}>
      {/* 상단 헤더 */}
      <header
        style={{
          height: 64,
          display: "flex",
          alignItems: "center",
          padding: "0 32px",
          backgroundColor: "#ffffff",
          boxShadow: "0 1px 4px rgba(0,0,0,0.05)",
        }}
      >
        {/* 로고 영역 */}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: "50%",
              border: "2px solid #2E6CCF",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 16,
              fontWeight: 700,
              color: "#2E6CCF",
            }}
          >
            CS
          </div>
          <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.1 }}>
            <span style={{ fontSize: 18, fontWeight: 700, color: "#2E6CCF" }}>
              CloudSaver
            </span>
            <span style={{ fontSize: 11, color: "#9ca3af" }}>
              Multi-Cloud Cost Optimizer
            </span>
          </div>
        </div>
      </header>

      {/* 본문 */}
      <main
        style={{
          padding: "40px 0",
          display: "flex",
          justifyContent: "center",
        }}
      >
        {step === "upload" && <UploadView onAnalyzeSuccess={handleAnalyzeSuccess} />}
        {step === "dashboard" && apiResult && (
          <DashboardView data={apiResult} onNew={handleNewAnalysis} />
        )}
      </main>
    </div>
  );
}

export default App;

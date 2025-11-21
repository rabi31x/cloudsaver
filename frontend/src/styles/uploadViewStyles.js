// src/styles/uploadViewStyles.js

export const container = {
  width: 720,
  backgroundColor: "#ffffff",
  borderRadius: 16,
  boxShadow: "0 10px 30px rgba(0,0,0,0.06)",
  padding: 32,
};

export const title = {
  fontSize: 28,
  marginBottom: 8,
};

export const subtitle = {
  fontSize: 13,
  color: "#6b7280",
  marginBottom: 24,
};

export const cloudTabs = {
  display: "flex",
  gap: 12,
  marginBottom: 24,
};

export const cloudButton = {
  flex: 1,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  gap: 8,
  borderRadius: 12,
  border: "1px solid #d1d5db",
  backgroundColor: "#ffffff",
  padding: "10px 16px",
  cursor: "pointer",
  fontWeight: 500,
};

export const cloudButtonActive = {
  border: "2px solid #2E6CCF",
  backgroundColor: "#eff6ff",
};

export const uploadBox = {
  borderRadius: 16,
  backgroundColor: "#f3f4f6",
  border: "1px dashed #d1d5db",
  height: 260,
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  gap: 16,
  transition: "all 0.15s ease-out",
};

export const uploadBoxActive = {
  backgroundColor: "#e5efff",
  borderColor: "#2E6CCF",
};

export const uploadIcon = {
  fontSize: 40,
};

export const uploadTitle = {
  fontSize: 16,
  fontWeight: 500,
};

export const uploadHint = {
  fontSize: 12,
  color: "#9ca3af",
};

export const analyzeButton = (loading) => ({
  padding: "10px 20px",
  borderRadius: 999,
  border: "none",
  backgroundColor: loading ? "#9ca3af" : "#2E6CCF",
  color: "#ffffff",
  fontWeight: 600,
  cursor: loading ? "default" : "pointer",
  boxShadow: "0 4px 10px rgba(46,108,207,0.3)",
});

export const errorText = {
  marginTop: 12,
  color: "#ef4444",
  fontSize: 13,
};

export const fileListText = {
  marginTop: 16,
  fontSize: 13,
};

// src/styles/dashboardViewStyles.js

// 기존 스타일 (유지)
export const container = {
  width: "90%",
  maxWidth: 1200,
  backgroundColor: "#ffffff",
  borderRadius: 16,
  boxShadow: "0 10px 30px rgba(0,0,0,0.06)",
  padding: 24,
  display: "flex",
  flexDirection: "column",
  gap: 16,
};

export const headerRow = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  marginBottom: 8,
};

export const pillButton = {
  padding: "8px 18px",
  borderRadius: 999,
  border: "none",
  backgroundColor: "#ffffff",
  boxShadow: "0 3px 10px rgba(0,0,0,0.06)",
  cursor: "pointer",
  fontSize: 13,
  fontWeight: 600,
};

export const mainRow = {
  display: "flex",
  gap: 24,
  minHeight: 420,
};

export const leftPane = {
  flex: 1.1,
  display: "flex",
  flexDirection: "column",
};

export const rightPane = {
  flex: 1,
  display: "flex",
  flexDirection: "column",
  gap: 16,
};

export const cloudTabs = {
  display: "flex",
  gap: 12,
  marginBottom: 16,
};

export const cloudTabButton = {
  flex: 1,
  borderRadius: 12,
  border: "1px solid #d1d5db",
  padding: "8px 12px",
  backgroundColor: "#ffffff",
  cursor: "pointer",
  fontSize: 13,
  fontWeight: 500,
};

export const cloudTabActive = {
  border: "2px solid #2E6CCF",
  backgroundColor: "#eff6ff",
};

export const solutionBox = {
  flex: 1,
  backgroundColor: "#f9fafb",
  borderRadius: 14,
  padding: 16,
  overflowY: "auto",
};

export const solutionCard = {
  backgroundColor: "#ffffff",
  borderRadius: 12,
  padding: 12,
  marginBottom: 10,
  boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
};

export const chartCard = {
  backgroundColor: "#ffffff",
  borderRadius: 14,
  border: "1px solid #e5e7eb",
  padding: 16,
  height: 220,
};

// ✨ 추가된 스타일
export const titleStyle = {
  fontSize: 26, 
  marginBottom: 4,
};

export const subtitleStyle = {
  fontSize: 13, 
  color: "#6b7280",
};

export const buttonGroupStyle = {
  display: "flex", 
  gap: 12,
};

export const emptySolutionStyle = {
  height: "100%",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  color: "#9ca3af",
  fontSize: 14,
};

export const cardHeaderStyle = {
  display: "flex",
  justifyContent: "space-between",
  marginBottom: 4,
  alignItems: "center",
};

export const cardTitleStyle = {
  fontWeight: 600,
};

export const categoryBadgeStyle = {
  fontSize: 11,
  padding: "2px 8px",
  borderRadius: 999,
  backgroundColor: "#eef2ff",
  color: "#4f46e5",
};

export const cardReasonStyle = {
  fontSize: 13, 
  color: "#6b7280", 
  marginBottom: 4,
};

export const cardCostStyle = {
  fontSize: 12, 
  color: "#9ca3af",
};

export const cardSourceStyle = {
  fontSize: 11, 
  color: "#d1d5db", 
  marginTop: 2,
};

export const chartTitleStyle = {
  fontSize: 14, 
  fontWeight: 600, 
  marginBottom: 8,
};

export const emptyChartStyle = {
  height: "100%",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  color: "#d1d5db",
  fontSize: 13,
};

export const dropdownContainer = {
    position: 'relative',
    display: 'inline-block',
};

export const dropdownMenu = {
    position: 'absolute',
    top: '100%',
    right: 0,
    backgroundColor: '#ffffff',
    borderRadius: 8,
    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
    zIndex: 10,
    minWidth: 150,
    marginTop: 4,
    overflow: 'hidden',
};

export const dropdownItem = {
    width: '100%',
    padding: '10px 15px',
    border: 'none',
    backgroundColor: 'transparent',
    textAlign: 'left',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 500,
};
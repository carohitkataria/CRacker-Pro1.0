import React, { createContext, useContext, useState } from "react";

const CurrencyContext = createContext(null);

export function CurrencyProvider({ children }) {
  const [mode, setMode] = useState(() => localStorage.getItem("cp_currency") || "INR");
  const update = (m) => {
    setMode(m);
    localStorage.setItem("cp_currency", m);
  };
  return (
    <CurrencyContext.Provider value={{ mode, setMode: update }}>
      {children}
    </CurrencyContext.Provider>
  );
}

export const useCurrency = () => useContext(CurrencyContext);

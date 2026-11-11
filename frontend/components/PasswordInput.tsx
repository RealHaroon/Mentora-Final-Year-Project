"use client";

import { useState } from "react";

export default function PasswordInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  const [visible, setVisible] = useState(false);

  return (
    <div style={{ position: "relative" }}>
      <input {...props} type={visible ? "text" : "password"} style={{ paddingRight: 56, ...props.style }} />
      <button
        type="button"
        onClick={() => setVisible((v) => !v)}
        style={{
          position: "absolute",
          right: 12,
          top: "50%",
          transform: "translateY(-50%)",
          background: "none",
          border: "none",
          color: "var(--green-700)",
          fontSize: "0.78rem",
          fontWeight: 600,
          cursor: "pointer",
          padding: 0,
        }}
      >
        {visible ? "Hide" : "Show"}
      </button>
    </div>
  );
}

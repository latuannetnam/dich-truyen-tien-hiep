"use client";

import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { CheckCircle, XCircle, X } from "lucide-react";

interface Toast {
  id: number;
  type: "success" | "error";
  message: string;
}

interface ToastContextType {
  showSuccess: (message: string) => void;
  showError: (message: string) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

let nextId = 0;

export default function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (type: "success" | "error", message: string) => {
      const id = nextId++;
      setToasts((prev) => [...prev, { id, type, message }]);
      const ms = type === "success" ? 3000 : 5000;
      setTimeout(() => removeToast(id), ms);
    },
    [removeToast]
  );

  const showSuccess = useCallback(
    (message: string) => addToast("success", message),
    [addToast]
  );

  const showError = useCallback(
    (message: string) => addToast("error", message),
    [addToast]
  );

  return (
    <ToastContext.Provider value={{ showSuccess, showError }}>
      {children}
      {/* Toast container */}
      <div
        className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 pointer-events-none"
        aria-live="assertive"
        role="alert"
      >
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    requestAnimationFrame(() => setVisible(true));
  }, []);

  const isSuccess = toast.type === "success";
  const bgClass = isSuccess
    ? "bg-[#10B981]/15 border-[#10B981]/30 text-[#10B981]"
    : "bg-[#EF4444]/15 border-[#EF4444]/30 text-[#EF4444]";

  return (
    <div
      className={`
        pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-lg border
        shadow-lg backdrop-blur-sm min-w-[320px] max-w-md
        transition-all duration-300 ease-out
        ${bgClass}
        ${visible ? "translate-x-0 opacity-100" : "translate-x-8 opacity-0"}
      `}
    >
      {isSuccess ? (
        <CheckCircle size={18} className="shrink-0" aria-hidden="true" />
      ) : (
        <XCircle size={18} className="shrink-0" aria-hidden="true" />
      )}
      <span className="text-sm font-medium flex-1">{toast.message}</span>
      <button
        onClick={onClose}
        className="shrink-0 p-0.5 rounded hover:bg-white/10 transition-colors cursor-pointer"
        aria-label="Dismiss"
      >
        <X size={14} aria-hidden="true" />
      </button>
    </div>
  );
}

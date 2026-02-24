"use client";

import { Check } from "lucide-react";

interface WizardStepsProps {
  steps: string[];
  currentStep: number;
}

export default function WizardSteps({ steps, currentStep }: WizardStepsProps) {
  return (
    <div className="flex items-center gap-0 mb-8">
      {steps.map((label, i) => {
        const stepNum = i + 1;
        const isActive = stepNum === currentStep;
        const isCompleted = stepNum < currentStep;
        const isFuture = stepNum > currentStep;

        return (
          <div key={label} className="flex items-center flex-1 last:flex-none">
            {/* Step circle + label */}
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={`
                  w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold
                  transition-colors duration-200
                  ${isCompleted ? "bg-[var(--color-success)] text-white" : ""}
                  ${isActive ? "bg-[var(--color-primary)] text-white" : ""}
                  ${isFuture ? "bg-[var(--bg-elevated)] text-[var(--text-muted)]" : ""}
                `}
                aria-current={isActive ? "step" : undefined}
              >
                {isCompleted ? <Check size={16} /> : stepNum}
              </div>
              <span
                className={`text-xs font-medium ${
                  isActive
                    ? "text-[var(--color-primary)]"
                    : isCompleted
                      ? "text-[var(--color-success)]"
                      : "text-[var(--text-muted)]"
                }`}
              >
                {label}
              </span>
            </div>

            {/* Connector line */}
            {i < steps.length - 1 && (
              <div
                className={`h-0.5 flex-1 mx-3 mt-[-20px] ${
                  stepNum < currentStep
                    ? "bg-[var(--color-primary)]"
                    : "bg-[var(--border-default)]"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

/**
 * FactCheckResults Component
 * 
 * Displays fact-checking results for claims made by the caller.
 * Shows verified claims (legitimate) and suspicious claims (red flags).
 * 
 * NOTE: This component is ready for use once fact-checking is integrated into agent.py.
 * See Backend/FACT_CHECK_INTEGRATION.md for backend integration steps.
 */

import { AlertTriangle, CheckCircle, Info } from "lucide-react";
import { GuardianAgentState } from "@/types/guardian";

interface FactCheckResultsProps {
  state: GuardianAgentState | null;
}

export function FactCheckResults({ state }: FactCheckResultsProps) {
  const factCheck = state?.fact_check;

  // Don't render if no fact-check data
  if (!factCheck) {
    return null;
  }

  const verifiedClaims = factCheck.verified_claims || [];
  const suspiciousClaims = factCheck.suspicious_claims || [];
  const riskIncrease = factCheck.risk_increase || 0;
  const confidence = factCheck.confidence || 0;

  // Don't render if no claims to show
  if (verifiedClaims.length === 0 && suspiciousClaims.length === 0) {
    return null;
  }

  // Color mapping for severity
  const getSeverityColor = (severity?: string) => {
    switch (severity) {
      case "high":
        return {
          bg: "bg-red-500/10",
          border: "border-red-500/30",
          text: "text-red-700 dark:text-red-300",
          icon: "text-red-600 dark:text-red-400",
        };
      case "medium":
        return {
          bg: "bg-orange-500/10",
          border: "border-orange-500/30",
          text: "text-orange-700 dark:text-orange-300",
          icon: "text-orange-600 dark:text-orange-400",
        };
      case "low":
        return {
          bg: "bg-yellow-500/10",
          border: "border-yellow-500/30",
          text: "text-yellow-700 dark:text-yellow-300",
          icon: "text-yellow-600 dark:text-yellow-400",
        };
      default:
        return {
          bg: "bg-gray-500/10",
          border: "border-gray-500/30",
          text: "text-gray-700 dark:text-gray-300",
          icon: "text-gray-600 dark:text-gray-400",
        };
    }
  };

  return (
    <div className="rounded-lg border border-border bg-card p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <Info className="h-5 w-5 text-primary" />
        <h3 className="text-base font-medium text-foreground">Claim Verification</h3>
      </div>

      {/* Summary */}
      {factCheck.summary && (
        <div className="mb-3 p-3 rounded-md bg-muted/30">
          <p className="text-sm text-muted-foreground">{factCheck.summary}</p>
        </div>
      )}

      {/* Suspicious Claims */}
      {suspiciousClaims.length > 0 && (
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="h-4 w-4 text-risk-high" />
            <p className="text-sm font-medium text-risk-high">
              Suspicious Claims ({suspiciousClaims.length})
            </p>
          </div>
          <div className="space-y-2">
            {suspiciousClaims.map((claim, index) => {
              const colors = getSeverityColor(claim.severity);
              return (
                <div
                  key={index}
                  className={`p-3 rounded-md border ${colors.bg} ${colors.border}`}
                >
                  <div className="flex items-start gap-2 mb-1">
                    <AlertTriangle className={`h-4 w-4 mt-0.5 flex-shrink-0 ${colors.icon}`} />
                    <div className="flex-1">
                      <p className={`text-sm font-medium ${colors.text}`}>
                        {claim.claim}
                      </p>
                      {claim.severity && (
                        <span className={`text-xs uppercase font-semibold ${colors.text}`}>
                          {claim.severity} severity
                        </span>
                      )}
                    </div>
                  </div>
                  {claim.problem && (
                    <p className="text-xs text-muted-foreground mt-1">
                      <span className="font-medium">Problem:</span> {claim.problem}
                    </p>
                  )}
                  {claim.reality && (
                    <p className="text-xs text-muted-foreground mt-1">
                      <span className="font-medium">Reality:</span> {claim.reality}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Verified Claims */}
      {verifiedClaims.length > 0 && (
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
            <p className="text-sm font-medium text-green-700 dark:text-green-300">
              Verified Claims ({verifiedClaims.length})
            </p>
          </div>
          <div className="space-y-2">
            {verifiedClaims.map((claim, index) => (
              <div
                key={index}
                className="p-3 rounded-md bg-green-500/10 border border-green-500/20"
              >
                <div className="flex items-start gap-2">
                  <CheckCircle className="h-4 w-4 mt-0.5 flex-shrink-0 text-green-600 dark:text-green-400" />
                  <div className="flex-1">
                    <p className="text-sm text-green-700 dark:text-green-300">
                      {claim.claim}
                    </p>
                    {claim.verification && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {claim.verification}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Risk Increase & Confidence */}
      <div className="flex justify-between items-center pt-2 border-t border-border">
        <div className="flex items-center gap-4">
          {riskIncrease > 0 && (
            <div className="flex items-center gap-1">
              <span className="text-xs text-muted-foreground">Risk Increase:</span>
              <span className="text-sm font-medium text-risk-high">
                +{riskIncrease.toFixed(0)}%
              </span>
            </div>
          )}
          <div className="flex items-center gap-1">
            <span className="text-xs text-muted-foreground">Confidence:</span>
            <span className="text-sm font-medium text-foreground">
              {(confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}


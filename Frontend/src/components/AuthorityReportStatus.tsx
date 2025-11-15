/**
 * AuthorityReportStatus Component
 * 
 * Displays the status of automated scam reporting to official authorities.
 * Shows when Guardian has reported a confirmed scam to FTC, FBI IC3, or Do Not Call Registry.
 * 
 * NOTE: This component is ready for use once authority reporting is integrated into agent.py.
 * See Backend/AUTHORITY_REPORTING_INTEGRATION.md for backend integration steps.
 */

import { CheckCircle, AlertTriangle, Info, Shield, ExternalLink } from "lucide-react";
import { GuardianAgentState } from "@/types/guardian";

interface AuthorityReportStatusProps {
  state: GuardianAgentState | null;
}

export function AuthorityReportStatus({ state }: AuthorityReportStatusProps) {
  const report = state?.authority_report;

  // Don't render if no authority report data
  if (!report) {
    return null;
  }

  // Don't render if skipped (not high enough confidence)
  if (report.status === "skipped") {
    return null;
  }

  // Don't render if disabled (browser_use not installed)
  if (report.status === "disabled") {
    return null;
  }

  const isSuccess = report.status === "success";
  const isFailed = report.status === "failed";

  return (
    <div 
      className={`rounded-lg border p-4 shadow-sm ${
        isSuccess 
          ? "bg-green-500/5 border-green-500/30" 
          : "bg-red-500/5 border-red-500/30"
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={`mt-0.5 ${isSuccess ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}>
          {isSuccess ? (
            <CheckCircle className="h-5 w-5" />
          ) : (
            <AlertTriangle className="h-5 w-5" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Shield className="h-4 w-4 text-primary" />
            <h3 className="text-base font-medium text-foreground">
              Authority Report
            </h3>
          </div>

          {/* Status Message */}
          <p className={`text-sm mb-2 ${
            isSuccess 
              ? "text-green-700 dark:text-green-300" 
              : "text-red-700 dark:text-red-300"
          }`}>
            {report.message}
          </p>

          {/* Authority Info */}
          {report.authority && (
            <div className="flex items-center gap-2 mb-2">
              <Info className="h-3.5 w-3.5 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">
                Reported to: <span className="font-medium text-foreground">{report.authority}</span>
              </p>
            </div>
          )}

          {/* Form Data (Success) */}
          {isSuccess && report.form_data && (
            <div className="mt-3 p-3 rounded-md bg-muted/30 border border-border">
              <p className="text-xs font-medium text-muted-foreground mb-2">Report Details:</p>
              <div className="space-y-1 text-xs text-muted-foreground">
                <div className="flex justify-between">
                  <span>Scammer Number:</span>
                  <span className="font-mono text-foreground">{report.form_data.scammer_number}</span>
                </div>
                <div className="flex justify-between">
                  <span>Risk Score:</span>
                  <span className="font-medium text-risk-high">{report.form_data.risk_score.toFixed(0)}%</span>
                </div>
                <div className="flex justify-between">
                  <span>Timestamp:</span>
                  <span className="text-foreground">
                    {new Date(report.form_data.timestamp).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Error Details (Failed) */}
          {isFailed && report.error && (
            <div className="mt-2 p-2 rounded-md bg-red-500/10 border border-red-500/20">
              <p className="text-xs text-red-700 dark:text-red-300">
                <span className="font-medium">Error:</span> {report.error}
              </p>
            </div>
          )}

          {/* External Link (if available) */}
          {report.authority_url && (
            <a
              href={report.authority_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 mt-2 text-xs text-primary hover:underline"
            >
              View reporting site
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </div>

      {/* Badge */}
      <div className="mt-3 pt-3 border-t border-border">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            {isSuccess ? "Scam successfully reported to authorities" : "Failed to report to authorities"}
          </span>
          <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
            isSuccess 
              ? "bg-green-500/20 text-green-700 dark:text-green-300" 
              : "bg-red-500/20 text-red-700 dark:text-red-300"
          }`}>
            {report.status.toUpperCase()}
          </span>
        </div>
      </div>
    </div>
  );
}


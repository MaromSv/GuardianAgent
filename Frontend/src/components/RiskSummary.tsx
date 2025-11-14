import { GuardianAgentState } from "@/types/guardian";
import { AlertCircle, CheckCircle, AlertTriangle } from "lucide-react";

interface RiskSummaryProps {
  state: GuardianAgentState | null;
}

export function RiskSummary({ state }: RiskSummaryProps) {
  const riskScore = state?.decision?.risk_score || state?.analysis?.risk_score || 0;
  const action = state?.decision?.action || "observe";
  const reason = state?.decision?.reason || state?.analysis?.reason || "Monitoring call";

  const getRiskLevel = (score: number): "low" | "medium" | "high" => {
    // Handle both 0-1 range and 0-100 range
    const normalizedScore = score > 1 ? score / 100 : score;
    if (normalizedScore < 0.3) return "low";
    if (normalizedScore < 0.7) return "medium";
    return "high";
  };

  const riskLevel = getRiskLevel(riskScore);

  const riskConfig = {
    low: {
      color: "text-risk-low",
      bg: "bg-risk-low/10",
      icon: CheckCircle,
      label: "Low risk",
    },
    medium: {
      color: "text-risk-medium",
      bg: "bg-risk-medium/10",
      icon: AlertTriangle,
      label: "Medium risk",
    },
    high: {
      color: "text-risk-high",
      bg: "bg-risk-high/10",
      icon: AlertCircle,
      label: "High risk – likely scam",
    },
  };

  const config = riskConfig[riskLevel];
  const Icon = config.icon;

  return (
    <div className="bg-card rounded-lg border border-border p-6">
      <h3 className="text-lg tracking-tight text-foreground mb-4">Risk Summary</h3>
      
      <div className={`${config.bg} rounded-lg p-4 mb-4`}>
        <div className="flex items-center gap-3 mb-2">
          <Icon className={`h-6 w-6 ${config.color}`} />
          <span className={`text-xl font-medium ${config.color}`}>{config.label}</span>
        </div>
        <p className="text-base text-foreground leading-relaxed">{reason}</p>
      </div>
      
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">Risk Score</span>
          <span className="text-base font-medium text-foreground">
            {riskScore > 1 ? riskScore.toFixed(0) : (riskScore * 100).toFixed(0)}%
          </span>
        </div>
        
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">Action</span>
          <span className="text-base font-medium text-foreground capitalize">{action}</span>
        </div>
        
        {state?.analysis?.confidence !== undefined && (
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Confidence</span>
            <span className="text-base font-medium text-foreground">
              {state.analysis.confidence > 1 ? state.analysis.confidence.toFixed(0) : (state.analysis.confidence * 100).toFixed(0)}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

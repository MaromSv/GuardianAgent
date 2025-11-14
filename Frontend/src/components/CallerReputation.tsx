import { GuardianAgentState } from "@/types/guardian";
import { Phone, AlertCircle, CheckCircle } from "lucide-react";

interface CallerReputationProps {
  state: GuardianAgentState | null;
}

export function CallerReputation({ state }: CallerReputationProps) {
  const reputation = state?.reputation_check;
  
  if (!reputation || !reputation.phone_number) {
    return (
      <div className="bg-card rounded-lg border border-border p-6">
        <h3 className="text-lg tracking-tight text-foreground mb-4">Caller Reputation</h3>
        <p className="text-base text-muted-foreground">Checking caller information...</p>
      </div>
    );
  }

  const isKnownScam = reputation.known_scam || false;
  const riskScore = reputation.risk_score || 0;

  return (
    <div className="bg-card rounded-lg border border-border p-6">
      <h3 className="text-lg tracking-tight text-foreground mb-4">Caller Reputation</h3>
      
      <div className="space-y-4">
        <div className="flex items-center gap-3 pb-3 border-b border-border">
          <Phone className="h-5 w-5 text-muted-foreground" />
          <span className="text-base text-foreground font-medium">{reputation.phone_number}</span>
        </div>
        
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Risk Score</span>
            <span className="text-base font-medium text-foreground">
              {riskScore > 1 ? riskScore.toFixed(0) : (riskScore * 100).toFixed(0)}%
            </span>
          </div>
          
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Status</span>
            <div className="flex items-center gap-2">
              {isKnownScam ? (
                <>
                  <AlertCircle className="h-4 w-4 text-risk-high" />
                  <span className="text-base font-medium text-risk-high">Known scam</span>
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 text-risk-low" />
                  <span className="text-base font-medium text-risk-low">Not flagged</span>
                </>
              )}
            </div>
          </div>
          
          {reputation.source && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Source</span>
              <span className="text-base text-foreground">{reputation.source}</span>
            </div>
          )}
        </div>
        
        {reputation.scam_type && (
          <div className="mt-4 p-3 bg-risk-high/10 border border-risk-high/20 rounded-lg">
            <p className="text-sm font-medium text-risk-high mb-1">Scam Details</p>
            <p className="text-sm text-foreground">{reputation.scam_type}</p>
          </div>
        )}
      </div>
    </div>
  );
}

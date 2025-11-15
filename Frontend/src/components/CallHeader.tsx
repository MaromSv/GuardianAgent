import { Lock } from "lucide-react";
import { GuardianAgentState } from "@/types/guardian";

interface CallHeaderProps {
  state: GuardianAgentState | null;
}

export function CallHeader({ state }: CallHeaderProps) {
  const formatDuration = (startTime?: number) => {
    if (!startTime) return "00:00";
    // startTime is Unix timestamp in seconds, convert to milliseconds
    const start = startTime * 1000;
    const now = Date.now();
    const seconds = Math.floor((now - start) / 1000);
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <header className="bg-card border-b border-border px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Logo on the left */}
          <img 
            src="/logo_notext.png" 
            alt="Guardian Agent" 
            className="h-10 w-auto"
          />
          <div className="flex flex-col justify-center">
            <h1 className="text-xl tracking-tight text-foreground font-medium leading-tight">Guardian Agent</h1>
            <p className="text-sm text-muted-foreground leading-tight">Call Monitoring</p>
          </div>
        </div>
        
        <div className="flex items-center gap-6">
          {state?.call_sid && (
            <div className="text-right">
              <p className="text-sm text-muted-foreground">Call ID</p>
              <p className="text-sm text-foreground font-mono font-medium">{state.call_sid}</p>
            </div>
          )}
          
          {state?.call_started_at && (
            <div className="text-right">
              <p className="text-sm text-muted-foreground">Duration</p>
              <p className="text-base text-foreground font-medium">{formatDuration(state.call_started_at)}</p>
            </div>
          )}
          
          <div className="flex items-center gap-2 px-3 py-2 bg-guardian-light rounded-lg">
            <Lock className="h-4 w-4 text-guardian-blue" />
            <span className="text-sm text-guardian-blue">Secure monitoring</span>
          </div>
        </div>
      </div>
    </header>
  );
}

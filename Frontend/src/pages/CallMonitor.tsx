import { useGuardianAgentState } from "@/hooks/useGuardianAgentState";
import { CallHeader } from "@/components/CallHeader";
import { ConversationView } from "@/components/ConversationView";
import { RiskSummary } from "@/components/RiskSummary";
import { CallerReputation } from "@/components/CallerReputation";
import { ActivityLog } from "@/components/ActivityLog";
import { Loader2 } from "lucide-react";

const CallMonitor = () => {
  // For demo, we don't need call_sid from URL - just fetch the global state
  const { state, isLoading, error } = useGuardianAgentState(undefined);

  if (isLoading && !state) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-xl text-foreground">Loading call data...</p>
        </div>
      </div>
    );
  }

  if (error && !state) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center max-w-md">
          <p className="text-xl text-destructive mb-2">Error loading call</p>
          <p className="text-base text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <CallHeader state={state} />
      
      <main className="flex-1 container mx-auto px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
          <div className="lg:col-span-2 h-[calc(100vh-180px)]">
            <ConversationView state={state} />
          </div>
          
          <div className="space-y-6 lg:h-[calc(100vh-180px)] overflow-y-auto">
            <RiskSummary state={state} />
            <CallerReputation state={state} />
            <ActivityLog state={state} />
          </div>
        </div>
      </main>
    </div>
  );
};

export default CallMonitor;

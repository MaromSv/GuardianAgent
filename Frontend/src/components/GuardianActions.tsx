import { GuardianAgentState } from "@/types/guardian";
import { Volume2, VolumeX, Shield, Search, Brain, Phone, MessageSquare, Loader2 } from "lucide-react";
import { useState } from "react";

interface GuardianActionsProps {
  state: GuardianAgentState | null;
}

// Map tool names to display info
const toolInfo: Record<string, { icon: typeof Shield; label: string; color: string }> = {
  phone_reputation_check: {
    icon: Phone,
    label: "Phone Number Check",
    color: "text-blue-600 dark:text-blue-400"
  },
  transcript_analysis: {
    icon: Brain,
    label: "Transcript Analysis",
    color: "text-purple-600 dark:text-purple-400"
  },
  web_search: {
    icon: Search,
    label: "Web Search",
    color: "text-green-600 dark:text-green-400"
  },
  decision_making: {
    icon: Shield,
    label: "Decision Making",
    color: "text-orange-600 dark:text-orange-400"
  },
  speech_generation: {
    icon: MessageSquare,
    label: "Generating Speech",
    color: "text-teal-600 dark:text-teal-400"
  }
};

export function GuardianActions({ state }: GuardianActionsProps) {
  const [isPlaying, setIsPlaying] = useState(false);

  // Simplified: Look for most recent tool in activity log
  let toolDisplay = null;
  let toolDescription = "";
  let isActive = false;
  
  // First check if there's an active tool
  if (state?.current_tool && state?.current_tool_description) {
    toolDisplay = toolInfo[state.current_tool] || null;
    toolDescription = state.current_tool_description;
    isActive = true;
  }
  // Otherwise check activity log for most recent tool
  else if (state?.activity && state.activity.length > 0) {
    for (let i = state.activity.length - 1; i >= 0; i--) {
      const entry = state.activity[i];
      if (entry.tool) {
        toolDisplay = toolInfo[entry.tool] || null;
        toolDescription = entry.tool_description || "";
        break;
      }
    }
  }
  
  // Debug: log what we have
  if (state?.activity && state.activity.length > 0) {
    console.log("Latest activity:", state.activity[state.activity.length - 1]);
    console.log("Tool display:", toolDisplay, toolDescription);
  }

  return (
    <div className="bg-card rounded-lg border border-border p-6 space-y-4">
      <h3 className="text-lg tracking-tight text-foreground">Guardian Status</h3>
      
      {/* Tool Activity Display */}
      {toolDisplay && toolDescription ? (
        <div className="bg-muted/50 rounded-lg p-4 border border-border/50">
          <div className="flex items-center gap-3">
            <div className="relative">
              <toolDisplay.icon className={`h-5 w-5 ${toolDisplay.color}`} />
              {isActive && (
                <Loader2 className="h-3 w-3 absolute -top-1 -right-1 animate-spin text-muted-foreground" />
              )}
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-foreground">{toolDisplay.label}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{toolDescription}</p>
            </div>
          </div>
        </div>
      ) : null}
      
      {/* Show monitoring message only if no tool activity */}
      {!toolDisplay && (
        <div className="text-center py-4">
          <p className="text-base text-muted-foreground">Guardian is monitoring...</p>
        </div>
      )}
    </div>
  );
}

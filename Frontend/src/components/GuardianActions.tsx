import { GuardianAgentState } from "@/types/guardian";
import { Volume2, VolumeX, Shield, Search, Brain, Phone, MessageSquare, Loader2, Database } from "lucide-react";
import { useState, useEffect, useRef } from "react";

interface GuardianActionsProps {
  state: GuardianAgentState | null;
}

// Minimum time to display each tool (in milliseconds)
const MIN_TOOL_DISPLAY_TIME = 2000; // 2 seconds

// Map tool names to display info
const toolInfo: Record<string, { icon: typeof Shield; label: string; color: string }> = {
  phone_reputation_check: {
    icon: Phone,
    label: "Phone Number Check",
    color: "text-blue-600 dark:text-blue-400"
  },
  speaker_identification: {
    icon: MessageSquare,
    label: "Speaker Identification",
    color: "text-cyan-600 dark:text-cyan-400"
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
  scam_database_update: {
    icon: Database,
    label: "Database Update",
    color: "text-red-600 dark:text-red-400"
  },
  speech_generation: {
    icon: MessageSquare,
    label: "Generating Speech",
    color: "text-teal-600 dark:text-teal-400"
  }
};

export function GuardianActions({ state }: GuardianActionsProps) {
  // State to persist tool display even after backend clears it
  const [displayedTool, setDisplayedTool] = useState<{
    tool: string;
    description: string;
    isActive: boolean;
  } | null>(null);
  
  const clearTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Check if there's an active tool from the backend
    if (state?.current_tool && state?.current_tool_description) {
      // Clear any existing timeout
      if (clearTimeoutRef.current) {
        clearTimeout(clearTimeoutRef.current);
        clearTimeoutRef.current = null;
      }
      
      // Update displayed tool immediately
      setDisplayedTool({
        tool: state.current_tool,
        description: state.current_tool_description,
        isActive: true
      });
    }
    // If backend cleared the tool but we're still displaying one
    else if (displayedTool && (!state?.current_tool || !state?.current_tool_description)) {
      // Mark as inactive (remove spinner)
      if (displayedTool.isActive) {
        setDisplayedTool({
          ...displayedTool,
          isActive: false
        });
      }
      
      // Set a timeout to clear the display after minimum display time
      if (!clearTimeoutRef.current) {
        clearTimeoutRef.current = setTimeout(() => {
          setDisplayedTool(null);
          clearTimeoutRef.current = null;
        }, MIN_TOOL_DISPLAY_TIME);
      }
    }
    
    // Cleanup timeout on unmount
    return () => {
      if (clearTimeoutRef.current) {
        clearTimeout(clearTimeoutRef.current);
      }
    };
  }, [state?.current_tool, state?.current_tool_description, displayedTool]);

  // Get display info for the current tool
  const toolDisplay = displayedTool ? toolInfo[displayedTool.tool] || null : null;
  const toolDescription = displayedTool?.description || "";
  const isActive = displayedTool?.isActive || false;

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
        <div className="text-center py-8">
          <div className="flex items-center justify-center gap-3 mb-3">
            <Shield className="h-6 w-6 text-muted-foreground animate-pulse" />
          </div>
          <p className="text-base text-muted-foreground flex items-center justify-center gap-1">
            Guardian is monitoring
            <span className="flex gap-0.5 ml-1">
              <span className="animate-bounce" style={{ animationDelay: '0ms' }}>.</span>
              <span className="animate-bounce" style={{ animationDelay: '150ms' }}>.</span>
              <span className="animate-bounce" style={{ animationDelay: '300ms' }}>.</span>
            </span>
          </p>
        </div>
      )}
    </div>
  );
}

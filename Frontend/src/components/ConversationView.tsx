import React, { useEffect, useRef, useState } from "react";
import { GuardianAgentState } from "@/types/guardian";
import { Shield, Phone, Brain, Search, MessageSquare } from "lucide-react";

interface ConversationViewProps {
  state: GuardianAgentState | null;
}

// Animated loading dots component
function LoadingDots() {
  return (
    <div className="flex items-center gap-1.5 px-5 py-3">
      <div className="w-2 h-2 rounded-full bg-muted-foreground/60 animate-[dot-bounce_1.4s_ease-in-out_infinite]" style={{ animationDelay: "0s" }} />
      <div className="w-2 h-2 rounded-full bg-muted-foreground/60 animate-[dot-bounce_1.4s_ease-in-out_infinite]" style={{ animationDelay: "0.2s" }} />
      <div className="w-2 h-2 rounded-full bg-muted-foreground/60 animate-[dot-bounce_1.4s_ease-in-out_infinite]" style={{ animationDelay: "0.4s" }} />
    </div>
  );
}

// Map tool names to display info
const toolIcons: Record<string, typeof Shield> = {
  phone_reputation_check: Phone,
  transcript_analysis: Brain,
  web_search: Search,
  decision_making: Shield,
  speech_generation: MessageSquare,
};

const toolLabels: Record<string, string> = {
  phone_reputation_check: "Checking caller reputation",
  transcript_analysis: "Analyzing conversation",
  web_search: "Searching online",
  decision_making: "Evaluating risk",
  speech_generation: "Generating response",
};

// Helper function to get color based on risk score
function getRiskColor(riskScore: number): { bg: string; border: string; text: string; label: string } {
  if (riskScore >= 80) {
    return {
      bg: "rgba(239, 68, 68, 0.15)",  // red-500 with opacity
      border: "rgba(239, 68, 68, 0.4)",
      text: "rgb(185, 28, 28)",  // red-700
      label: "rgb(239, 68, 68)"   // red-500
    };
  } else if (riskScore >= 60) {
    return {
      bg: "rgba(249, 115, 22, 0.15)",  // orange-500 with opacity
      border: "rgba(249, 115, 22, 0.4)",
      text: "rgb(194, 65, 12)",  // orange-700
      label: "rgb(249, 115, 22)"  // orange-500
    };
  } else if (riskScore >= 30) {
    return {
      bg: "rgba(234, 179, 8, 0.15)",  // yellow-500 with opacity
      border: "rgba(234, 179, 8, 0.4)",
      text: "rgb(161, 98, 7)",  // yellow-700
      label: "rgb(234, 179, 8)"  // yellow-500
    };
  } else {
    return {
      bg: "rgba(107, 114, 128, 0.1)",  // gray-500 with opacity
      border: "rgba(107, 114, 128, 0.2)",
      text: "rgb(55, 65, 81)",  // gray-700
      label: "rgb(107, 114, 128)"  // gray-500
    };
  }
}

export function ConversationView({ state }: ConversationViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [lastTranscriptLength, setLastTranscriptLength] = useState(0);
  const [showLoading, setShowLoading] = useState(false);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [state?.transcript]);

  // Track transcript changes to show/hide loading indicator
  useEffect(() => {
    const currentLength = state?.transcript?.length || 0;
    
    if (currentLength > lastTranscriptLength) {
      // New message arrived, hide loading
      setShowLoading(false);
      setLastTranscriptLength(currentLength);
    } else if (currentLength > 0 && currentLength === lastTranscriptLength) {
      // Same length, show loading after a delay
      const timer = setTimeout(() => {
        setShowLoading(true);
      }, 2000); // Show loading after 2 seconds of no new messages
      return () => clearTimeout(timer);
    } else {
      setLastTranscriptLength(currentLength);
    }
  }, [state?.transcript, lastTranscriptLength]);

  const hasTranscript = state?.transcript && state.transcript.length > 0;
  const isCallActive = state?.call_sid && state?.call_started_at;
  
  // Determine Guardian status
  let guardianStatus = "Observing call";
  let guardianIcon = Shield;
  let isWorking = false;
  
  if (state?.current_tool && state?.current_tool_description) {
    guardianStatus = state.current_tool_description;
    guardianIcon = toolIcons[state.current_tool] || Shield;
    isWorking = true;
    console.log("🔧 Active tool:", state.current_tool, "-", guardianStatus);
  } else if (state?.activity && state.activity.length > 0) {
    // Check recent activity for tool usage
    const recentActivity = state.activity[state.activity.length - 1];
    if (recentActivity?.tool) {
      guardianStatus = recentActivity.tool_description || toolLabels[recentActivity.tool] || "Processing";
      guardianIcon = toolIcons[recentActivity.tool] || Shield;
      console.log("📋 Recent tool from activity:", recentActivity.tool, "-", guardianStatus);
    } else if (recentActivity?.stage === "check_reputation") {
      guardianStatus = "Checking caller reputation";
      guardianIcon = Phone;
      console.log("📋 Phone check from stage:", recentActivity.stage);
    }
  }

  return (
    <div className="flex flex-col h-full bg-card rounded-lg border border-border">
      <div className="px-6 py-4 border-b border-border">
        <h2 className="text-lg tracking-tight text-foreground">Conversation</h2>
        {state?.user_number && state?.caller_number && (
          <p className="text-sm text-muted-foreground mt-1">
            {state.user_number} ↔ {state.caller_number}
          </p>
        )}
      </div>
      
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4 pb-24">
        {!hasTranscript && (
          <div className="flex items-center justify-center h-full">
            <p className="text-muted-foreground text-lg">Waiting for conversation to start...</p>
          </div>
        )}
        
        {state?.transcript?.map((entry, index) => {
          const speaker = entry.speaker;
          const isGuardian = speaker === "guardian";
          const isUser = speaker === "user";
          const isCaller = speaker === "caller";
          
          // Get current risk score for dynamic caller coloring
          const currentRisk = state?.analysis?.risk_score || state?.reputation_check?.risk_score || 0;
          const riskColors = isCaller ? getRiskColor(currentRisk) : null;
          
          return (
            <div key={index} className={`flex ${isUser || isGuardian ? "justify-start" : "justify-end"}`}>
              <div 
                className={`max-w-[70%] rounded-2xl px-5 py-3 transition-all duration-500 ${
                  isGuardian
                    ? "bg-green-500/10 border-2 border-green-500/40 shadow-sm"
                    : isUser
                    ? "bg-blue-500/10 border border-blue-500/20"
                    : ""
                }`}
                style={isCaller && riskColors ? {
                  backgroundColor: riskColors.bg,
                  borderWidth: "1px",
                  borderStyle: "solid",
                  borderColor: riskColors.border,
                } : {}}
              >
                <div className="flex items-center gap-2 mb-1">
                  {isGuardian && <Shield className="h-4 w-4 text-green-600 dark:text-green-400" />}
                  <p 
                    className={`text-sm font-medium ${
                      isGuardian
                        ? "text-green-700 dark:text-green-300"
                        : isUser
                        ? "text-blue-700 dark:text-blue-300"
                        : ""
                    }`}
                    style={isCaller && riskColors ? { color: riskColors.text } : {}}
                  >
                    {isGuardian ? "Guardian" : isUser ? "You" : "Caller"}
                  </p>
                  {isCaller && currentRisk > 0 && (
                    <span 
                      className="text-xs font-semibold px-2 py-0.5 rounded-full transition-all duration-500"
                      style={riskColors ? {
                        backgroundColor: riskColors.label + "20",
                        color: riskColors.label,
                      } : {}}
                    >
                      {currentRisk.toFixed(0)}% risk
                    </span>
                  )}
                </div>
                <p 
                  className={`text-base leading-relaxed ${
                    isGuardian
                      ? "text-green-900 dark:text-green-100"
                      : isUser
                      ? "text-blue-900 dark:text-blue-100"
                      : ""
                  }`}
                  style={isCaller && riskColors ? { color: riskColors.text } : {}}
                >
                  {entry.text}
                </p>
              </div>
            </div>
          );
        })}
        
        {/* Loading indicator - shows when call is active but waiting for next message */}
        {isCallActive && hasTranscript && showLoading && (
          <div className="flex justify-end">
            <div className="max-w-[70%] rounded-2xl bg-muted/50 border border-border/50">
              <LoadingDots />
            </div>
          </div>
        )}
      </div>
      
      {/* Guardian Status Bar - Fixed at bottom */}
      <div className="border-t border-border bg-muted/30 backdrop-blur-sm">
        <div className="px-6 py-3 flex items-center justify-center gap-3">
          <div className="relative">
            {React.createElement(guardianIcon, {
              className: `h-5 w-5 text-green-600 dark:text-green-400 ${isWorking ? 'animate-pulse' : ''}`
            })}
          </div>
          <div className="flex items-center gap-2">
            <p className="text-sm text-foreground">
              {guardianStatus}
            </p>
            {isWorking && (
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-green-600 dark:bg-green-400 animate-[dot-pulse_1.5s_ease-in-out_infinite]" style={{ animationDelay: "0s" }} />
                <div className="w-1.5 h-1.5 rounded-full bg-green-600 dark:bg-green-400 animate-[dot-pulse_1.5s_ease-in-out_infinite]" style={{ animationDelay: "0.3s" }} />
                <div className="w-1.5 h-1.5 rounded-full bg-green-600 dark:bg-green-400 animate-[dot-pulse_1.5s_ease-in-out_infinite]" style={{ animationDelay: "0.6s" }} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

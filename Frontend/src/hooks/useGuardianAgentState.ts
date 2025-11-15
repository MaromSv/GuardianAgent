import { useState, useEffect, useCallback } from "react";
import { GuardianAgentState, StateResponse } from "@/types/guardian";

// For demo: use Vite dev-server proxy at /api → http://127.0.0.1:5000
const BACKEND_BASE_URL = "/api";
const POLL_INTERVAL = 2500; // 2.5 seconds

export function useGuardianAgentState(callSid: string | undefined) {
  const [state, setState] = useState<GuardianAgentState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchState = useCallback(async () => {
    // For demo, we don't need callSid - just fetch the global state
    try {
      console.log(`[DEBUG] Fetching global call state from /calls/state`);
      const response = await fetch(`${BACKEND_BASE_URL}/calls/state`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch state: ${response.statusText}`);
      }

      const data: StateResponse = await response.json();
      console.log("[DEBUG] Raw response:", data);
      
      // Backend returns { state: { values: GuardianAgentState } }
      const stateValues = data.state?.values || null;
      console.log("[DEBUG] Extracted state values:", stateValues);
      
      if (stateValues) {
        console.log("[DEBUG] State summary:", {
          call_sid: stateValues.call_sid,
          transcript_length: stateValues.transcript?.length || 0,
          current_tool: stateValues.current_tool,
          tool_description: stateValues.current_tool_description,
          risk_score: stateValues.decision?.risk_score || stateValues.analysis?.risk_score || 0,
          action: stateValues.decision?.action,
          caller_number: stateValues.caller_number,
          user_number: stateValues.user_number,
        });
        
        if (stateValues.transcript && stateValues.transcript.length > 0) {
          console.log("[DEBUG] Latest transcript entries:", 
            stateValues.transcript.slice(-3).map(entry => ({
              speaker: entry.speaker,
              text: entry.text
            }))
          );
        }
      }
      
      setState(stateValues);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch call state");
      console.error("[DEBUG] Error fetching call state:", err);
    } finally {
      setIsLoading(false);
    }
  }, []); // No dependencies - just poll the global state

  useEffect(() => {
    fetchState();
    const interval = setInterval(fetchState, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchState]);

  return { state, isLoading, error };
}

import { useState, useEffect, useCallback } from "react";
import { GuardianAgentState, StateResponse } from "@/types/guardian";

const BACKEND_BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL || "http://localhost:5000";
const POLL_INTERVAL = 2500; // 2.5 seconds

export function useGuardianAgentState(callSid: string | undefined) {
  const [state, setState] = useState<GuardianAgentState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchState = useCallback(async () => {
    if (!callSid) {
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch(`${BACKEND_BASE_URL}/calls/${callSid}/state`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch state: ${response.statusText}`);
      }

      const data: StateResponse = await response.json();
      // Backend returns { state: { values: GuardianAgentState } }
      setState(data.state?.values || null);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch call state");
      console.error("Error fetching call state:", err);
    } finally {
      setIsLoading(false);
    }
  }, [callSid]);

  useEffect(() => {
    fetchState();
    const interval = setInterval(fetchState, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchState]);

  return { state, isLoading, error };
}

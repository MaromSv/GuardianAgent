export interface TranscriptEntry {
  speaker: "user" | "caller" | "guardian";
  text: string;
}

export interface ReputationCheck {
  phone_number?: string;
  risk_score?: number;
  known_scam?: boolean;
  source?: string;
}

export interface Analysis {
  risk_score?: number;
  confidence?: number;
  reason?: string;
}

export interface Decision {
  action?: "observe" | "question" | "warn";
  reason?: string;
  risk_score?: number;
}

export interface ActivityEntry {
  stage: string;
  data?: any;
  tool?: string;
  tool_description?: string;
}

export interface GuardianAgentState {
  call_sid?: string;
  user_number?: string;
  caller_number?: string;
  call_started_at?: number; // Unix timestamp (epoch seconds)
  transcript?: TranscriptEntry[];
  reputation_check?: ReputationCheck;
  analysis?: Analysis;
  decision?: Decision;
  guardian_utterance_text?: string;
  guardian_utterance_audio_url?: string;
  activity?: ActivityEntry[];
  scam_processed?: boolean;
  current_tool?: string; // e.g., "phone_reputation_check", "transcript_analysis", "web_search", "decision_making"
  current_tool_description?: string; // Human-readable description
}

export interface StateResponse {
  state: {
    values: GuardianAgentState;
  };
}

export interface TranscriptEntry {
  speaker: "user" | "caller" | "guardian";
  text: string;
}

export interface ReputationCheck {
  phone_number?: string;
  risk_score?: number;
  known_scam?: boolean;
  source?: string;
  scam_type?: string;
  database_match?: boolean;
  match_type?: string;
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

export interface FactCheckClaim {
  claim: string;
  verification?: string;
  problem?: string;
  reality?: string;
  severity?: "high" | "medium" | "low";
}

export interface FactCheck {
  verified_claims?: FactCheckClaim[];
  suspicious_claims?: FactCheckClaim[];
  risk_increase?: number; // 0-50
  confidence?: number; // 0.0-1.0
  summary?: string;
  model?: string;
}

export interface ActivityEntry {
  stage: string;
  data?: any;
  tool?: string;
  tool_description?: string;
}

export interface AuthorityReport {
  status: "success" | "failed" | "skipped" | "disabled";
  authority?: string;
  authority_url?: string;
  message: string;
  form_data?: {
    scammer_number: string;
    victim_number: string;
    risk_score: number;
    timestamp: string;
  };
  error?: string;
}

export interface GuardianAgentState {
  call_sid?: string;
  user_number?: string;
  caller_number?: string;
  call_started_at?: number; // Unix timestamp (epoch seconds)
  transcript?: TranscriptEntry[];
  reputation_check?: ReputationCheck;
  analysis?: Analysis;
  fact_check?: FactCheck; // Fact-checking results (validates caller's claims)
  decision?: Decision;
  guardian_utterance_text?: string;
  guardian_utterance_audio_url?: string;
  activity?: ActivityEntry[];
  scam_processed?: boolean;
  authority_report?: AuthorityReport; // Report to official authorities (FTC, FBI, etc.)
  current_tool?: string; // e.g., "phone_reputation_check", "transcript_analysis", "fact_checking", "authority_reporting", "web_search", "decision_making"
  current_tool_description?: string; // Human-readable description
}

export interface StateResponse {
  state: {
    values: GuardianAgentState;
  };
}

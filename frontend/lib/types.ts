export type ActionMini = {
  ticker: string;
  polished_reduction?: number | null;
  bits?: string | null;
  current_weight?: number | null;
  final_weight?: number | null;
  quantum_reduction?: number | null;
  sell_value?: number | null;
};

export type PipelineStage = {
  key: string;
  step: string;
  name: string;
  description: string;
  status: string;
};

export type ConsoleShell = {
  online: boolean;
  profile_id: string;
  profile_status: string;
  config_version: string;
  scenario_count: number | null;
  candidate_count: number;
};

export type ConsoleOverview = {
  online: boolean;
  profile_id: string;
  profile_status: string;
  config_version: string;
  candidate_count: number;
  scenario_count: number | null;
  actual_solver: string | null;
  true_cvar_before: number | null;
  true_cvar_after: number | null;
  true_cvar_relative_reduction: number | null;
  materiality_met: boolean | null;
  transaction_cost: number | null;
  turnover: number | null;
  constraints_passed: boolean | null;
  warnings: string[];
  top_actions: ActionMini[];
  pipeline: PipelineStage[];
  stage_status: Record<string, string>;
};

export type DataQualityRow = {
  check_id?: string | null;
  check_name?: string | null;
  status?: string | null;
  type?: string | null;
  count?: number | null;
  trace?: string | null;
};

export type ConsoleData = {
  online: boolean;
  stage_status: string;
  config_version: string;
  manifest_present: boolean;
  universe_count: number;
  evidence_count: number;
  checks_passed: number;
  checks_total: number;
  data_quality: DataQualityRow[];
  universe: { ticker?: string | null; company_name?: string | null; exchange?: string | null }[];
  adjusted_close_evidence: Record<string, unknown>[];
  data_manifest: Record<string, unknown> | null;
};

export type RegimePoint = {
  date: string;
  regime: string;
  prob_normal: number;
  prob_volatile: number;
  prob_stress: number;
};

export type ConsoleRegime = {
  online: boolean;
  stage_status: string;
  gate_status: string | null;
  run_mode: string | null;
  champion: Record<string, unknown>;
  coverage: Record<string, unknown>;
  label_map: Record<string, string>;
  occupancy: Record<string, unknown>;
  latest: RegimePoint | null;
  timeline: RegimePoint[];
};

export type ScenarioValidationRow = {
  target_regime: string;
  metric: string;
  scenario_value: number;
  reference_value: number;
  statistic: number;
  verdict: string;
};

export type ConsoleScenarios = {
  online: boolean;
  stage_status: string;
  gate_status: string;
  target_regime: string;
  evaluation_date: string;
  num_scenarios: number;
  horizon_days: number;
  n_assets: number | null;
  block_length: number | null;
  seed: number | string | null;
  return_type: string | null;
  anchor_first: string | null;
  anchor_last: string | null;
  reuse_rate: number | null;
  ticker_order: string[];
  validation: ScenarioValidationRow[];
  n_fail: number;
  primary: Record<string, unknown>;
};

export type CandidateRow = {
  rank?: number | null;
  ticker?: string | null;
  selected_top10: boolean;
  eligible_status: boolean;
  net_risk_score?: number | null;
  baseline_cvar_contribution?: number | null;
  transaction_cost_estimate?: number | null;
  liquidity_penalty?: number | null;
  reason?: string | null;
  current_weight?: number | null;
};

export type ConsoleRisk = {
  online: boolean;
  profile_id: string;
  profile_status: string;
  candidate_count: number;
  true_cvar_before: number | null;
  true_cvar_after: number | null;
  transaction_cost: number | null;
  turnover: number | null;
  materiality_met: boolean | null;
  materiality_threshold: number | null;
  top_candidate: CandidateRow | null;
  candidates: CandidateRow[];
  risk_summary: Record<string, unknown> | null;
};

export type ConsoleQuantum = {
  online: boolean;
  actual_solver: string | null;
  requested_solver: string | null;
  constraints_passed: boolean | null;
  winning_bitstring: string | null;
  true_cvar_before: number | null;
  true_cvar_after: number | null;
  caveat: string | null;
  exact_best_energy: number | null;
  mean_feasibility_rate: number | null;
  classical_energy: number | null;
  optimality_gap: number | null;
  qaoa_beats_classical: boolean | null;
  source_artifact: string | null;
  actions: ActionMini[];
  workflow_benchmark: Record<string, unknown> | null;
  qubo_model: Record<string, unknown> | null;
  exact_solution: Record<string, unknown> | null;
};

export type ConsoleReport = {
  online: boolean;
  profile_id: string;
  profile_status: string;
  config_version: string;
  universe_count: number;
  scenario_count: number | null;
  actual_solver: string | null;
  true_cvar_before: number | null;
  true_cvar_after: number | null;
  transaction_cost: number | null;
  turnover: number | null;
  materiality_met: boolean | null;
  warnings: string[];
  stage_status: Record<string, string>;
  top_actions: ActionMini[];
  run_id: string | null;
  logs_tail: string[];
  metrics: Record<string, unknown> | null;
};

export type NavIconName =
  | "gauge"
  | "database"
  | "activity"
  | "waves"
  | "shield"
  | "atom"
  | "file";

export type NavItem = {
  href: string;
  icon: NavIconName;
  title: string;
  desc: string;
  section: "workspace" | "decision";
};

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(
  path: string,
  opts: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { ...opts, headers });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface AuthResponse {
  user_id: string;
  token: string;
}

export function register(email: string, password: string) {
  return request<AuthResponse>("/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function login(email: string, password: string) {
  return request<AuthResponse>("/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

// ── Intake ────────────────────────────────────────────────────────────────────

export interface IntakePayload {
  age: number;
  sex: string;
  parq_flags: string[];
  medication_class: string;
  joint_flags: string[];
  functional_tests: {
    sit_to_stand_count: number;
    pushup_max: number;
    single_leg_stand_s: number;
  };
  days_per_week: number;
  minutes_per_session: number;
  fall_risk: boolean;
  equipment: string[];
  goals: string[];
}

export interface IntakeSubmitResponse {
  intake_id: string;
  clearance_required: boolean;
  clearance_reason: string | null;
  hypo_risk: string | null;
}

export function submitIntake(user_id: string, intake: IntakePayload, token: string) {
  return request<IntakeSubmitResponse>("/v1/intake/submit", {
    method: "POST",
    body: JSON.stringify({ user_id, intake }),
  }, token);
}

// ── Program ───────────────────────────────────────────────────────────────────

export interface ExerciseInstance {
  exercise_id: string;
  sets: number;
  reps_or_time: string;
  rest_s: number;
  target_rpe: number;
  regression_alt: string;
  progression_alt: string;
}

export interface Block {
  name: string;
  exercises: ExerciseInstance[];
}

export interface Session {
  week: number;
  day: number;
  blocks: Block[];
  glucose_check_required: boolean;
  preferred_window: string | null;
}

export interface Week {
  week_number: number;
  sessions: Session[];
  is_deload: boolean;
}

export interface Program {
  engine_version: string;
  hypo_risk: string;
  rules_applied: string[];
  weeks: Week[];
}

export interface GenerateResponse {
  program_id: string;
  clearance_required: boolean;
  clearance_reason: string | null;
  program: Program | null;
}

export function generateProgram(user_id: string, intake_id: string, token: string) {
  return request<GenerateResponse>("/v1/programs/generate-from-intake", {
    method: "POST",
    body: JSON.stringify({ user_id, intake_id }),
  }, token);
}

export function getProgram(program_id: string, user_id: string, token: string) {
  return request<GenerateResponse>(`/v1/programs/${program_id}?user_id=${user_id}`, {}, token);
}

// ── Coaching ──────────────────────────────────────────────────────────────────

export interface CoachingResponse {
  coaching_text: string | null;
}

export function getCoaching(
  program_id: string,
  week: number,
  day: number,
  user_id: string,
  token: string,
) {
  return request<CoachingResponse>(
    `/v1/programs/${program_id}/sessions/${week}/${day}/coaching?user_id=${user_id}`,
    {},
    token,
  );
}

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type ApiHealth = {
  status: string;
  database?: string;
};

export type StorySummary = {
  id: string;
  slug: string;
  title: string;
  summary?: string | null;
  status: string;
  updated_at: string;
  evidence_count: number;
  latest_evidence_at?: string | null;
};

export type StoryEntity = {
  id: string;
  entity_type: string;
  slug: string;
  display_name: string;
  relation_type: string;
  confidence: number;
  match_method: string;
  matched_alias?: string | null;
};

export type StoryEvidence = {
  id: string;
  presentation_type: string;
  source_type: string;
  source_name: string;
  source_url?: string | null;
  published_at?: string | null;
  captured_at: string;
  author_or_speaker?: string | null;
  normalized_claim?: string | null;
  raw_excerpt_or_reference?: string | null;
  reliability_class?: string | null;
  directness?: string | null;
  metadata: Record<string, unknown>;
};

export type StoryDetail = {
  id: string;
  slug: string;
  title: string;
  summary?: string | null;
  status: string;
  significance: number;
  confidence: string;
  what_changed?: string | null;
  why_it_matters?: string | null;
  what_to_watch_next?: string | null;
  created_at: string;
  updated_at: string;
  entities: StoryEntity[];
  evidence: StoryEvidence[];
};

export type TeamSummary = {
  id: string;
  slug: string;
  name: string;
  active_season?: number | null;
  driver_count: number;
  story_count: number;
};

export type TeamMember = {
  id: string;
  slug: string;
  display_name: string;
  role: string;
  season: number;
  car_number?: number | null;
};

export type TeamDetail = {
  id: string;
  slug: string;
  name: string;
  active_season?: number | null;
  members: TeamMember[];
  stories: StorySummary[];
};

export type RaceSummary = {
  id: string;
  season: number;
  round?: number | null;
  slug: string;
  official_name: string;
  circuit?: string | null;
  country?: string | null;
  start_at?: string | null;
  weekend_start_date?: string | null;
  weekend_end_date?: string | null;
  status: string;
  story_count: number;
};

export type RaceDetail = RaceSummary & {
  synthesis?: string | null;
  stories: StorySummary[];
};

async function fetchJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${apiBaseUrl}${path}`, { cache: "no-store" });
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export async function getApiHealth(): Promise<ApiHealth | null> {
  try {
    const response = await fetch(`${apiBaseUrl}/health`, {
      next: { revalidate: 30 },
    });

    if (!response.ok) return null;
    return (await response.json()) as ApiHealth;
  } catch {
    return null;
  }
}

export function getStories(): Promise<StorySummary[]> {
  return fetchJson<StorySummary[]>("/api/v1/stories", []);
}

export function getStory(slug: string): Promise<StoryDetail | null> {
  return fetchJson<StoryDetail | null>(`/api/v1/stories/${encodeURIComponent(slug)}`, null);
}

export function getTeams(): Promise<TeamSummary[]> {
  return fetchJson<TeamSummary[]>("/api/v1/teams", []);
}

export function getTeam(slug: string): Promise<TeamDetail | null> {
  return fetchJson<TeamDetail | null>(`/api/v1/teams/${encodeURIComponent(slug)}`, null);
}

export function getRaces(): Promise<RaceSummary[]> {
  return fetchJson<RaceSummary[]>("/api/v1/races", []);
}

export function getRace(slug: string): Promise<RaceDetail | null> {
  return fetchJson<RaceDetail | null>(`/api/v1/races/${encodeURIComponent(slug)}`, null);
}

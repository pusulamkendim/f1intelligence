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

export async function getApiHealth(): Promise<ApiHealth | null> {
  try {
    const response = await fetch(`${apiBaseUrl}/health`, {
      next: { revalidate: 30 },
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as ApiHealth;
  } catch {
    return null;
  }
}

export async function getStories(): Promise<StorySummary[]> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/stories`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return [];
    }

    return (await response.json()) as StorySummary[];
  } catch {
    return [];
  }
}

export async function getStory(slug: string): Promise<StoryDetail | null> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/stories/${encodeURIComponent(slug)}`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as StoryDetail;
  } catch {
    return null;
  }
}

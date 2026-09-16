const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type ApiHealth = {
  status: string;
  database?: string;
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

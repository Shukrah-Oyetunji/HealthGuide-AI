
const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// ---------------------------------------------
// Types
// ---------------------------------------------

export interface User {
  id: number;
  name: string;
  email: string;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface QuestionHistoryItem {
  id: number;
  question: string;
  created_at: string;
}

export interface HealthSource {
  id: number;
  title: string;
  source: string;
  url: string | null;
  page: number | null;
}

export interface AskResponse {
  question_id: number;
  question: string;
  answer: string;
  sources: HealthSource[];
  evidence_count: number;
  has_evidence: boolean;
  providers_unavailable: string[];
}

// Health Library types

export interface LibraryItem {
  id: number;
  question: string;
  topic: string | null;
  created_at: string;
}

export interface LibraryQuestionDetail extends LibraryItem {
  answer: string | null;
  sources: HealthSource[];
}

// ---------------------------------------------
// Reusable API Request Function
// ---------------------------------------------

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = data?.detail;

    const message =
      typeof detail === "string"
        ? detail
        : "Request failed. Please try again.";

    throw new Error(message);
  }

  return data as T;
}

// ---------------------------------------------
// Authentication Headers
// ---------------------------------------------

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem("healthguide_token");

  if (!token) {
    throw new Error("Please sign in to continue.");
  }

  return {
    Authorization: `Bearer ${token}`,
  };
}

// ---------------------------------------------
// Authentication
// ---------------------------------------------

export async function registerUser(input: {
  name: string;
  email: string;
  password: string;
}): Promise<User> {
  return request<User>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function loginUser(input: {
  email: string;
  password: string;
}): Promise<LoginResponse> {
  const result = await request<LoginResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });

  localStorage.setItem("healthguide_token", result.access_token);

  return result;
}

export async function getCurrentUser(): Promise<User> {
  return request<User>("/api/auth/me", {
    headers: getAuthHeaders(),
  });
}

export function logoutUser(): void {
  localStorage.removeItem("healthguide_token");
}

// ---------------------------------------------
// Health Interests
// ---------------------------------------------

export async function getHealthInterests(): Promise<string[]> {
  return request<string[]>("/api/dashboard/interests", {
    headers: getAuthHeaders(),
  });
}

export async function saveHealthInterests(
  interests: string[],
): Promise<{ interests: string[] }> {
  return request<{ interests: string[] }>(
    "/api/dashboard/interests",
    {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify({ interests }),
    },
  );
}

// ---------------------------------------------
// Question History
// ---------------------------------------------

export async function getQuestionHistory(): Promise<
  QuestionHistoryItem[]
> {
  return request<QuestionHistoryItem[]>(
    "/api/dashboard/questions",
    {
      headers: getAuthHeaders(),
    },
  );
}

export async function saveQuestionHistory(
  question: string,
): Promise<QuestionHistoryItem> {
  return request<QuestionHistoryItem>(
    "/api/dashboard/questions",
    {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ question }),
    },
  );
}

// ---------------------------------------------
// Health Library
// ---------------------------------------------

// Retrieve all saved questions for the signed-in user.

export async function getHealthLibrary(): Promise<LibraryItem[]> {
  return request<LibraryItem[]>("/api/library", {
    headers: getAuthHeaders(),
  });
}

// Retrieve one saved question with its answer and sources.

export async function getLibraryQuestion(
  questionId: number,
): Promise<LibraryQuestionDetail> {
  return request<LibraryQuestionDetail>(
    `/api/library/${questionId}`,
    {
      headers: getAuthHeaders(),
    },
  );
}

// ---------------------------------------------
// HealthGuide AI - Ask a Health Question
// ---------------------------------------------

export async function askHealthQuestion(
  question: string,
): Promise<AskResponse> {
  return request<AskResponse>("/api/ask", {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ question }),
  });
}

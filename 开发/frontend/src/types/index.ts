export type Role = "user" | "reviewer" | "admin";
export type PublicationStatus =
  | "draft"
  | "pending_review"
  | "published"
  | "rejected"
  | "archived";

export interface User {
  id: number;
  email: string;
  display_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  github_username?: string | null;
  gitee_username?: string | null;
  real_name?: string | null;
  avatar_url?: string | null;
}

export interface Lesson {
  id: number;
  slug: string;
  title: string;
  objective: string;
  body_markdown: string;
  practice: string;
  completion_criteria: string;
  estimated_minutes: number;
  order_index: number;
}

export interface Course {
  id: number;
  slug: string;
  title: string;
  summary: string;
  prerequisites: string;
  difficulty: string;
  order_index: number;
  is_standalone: boolean;
  directory_collapsible: boolean;
  lessons: Lesson[];
}

export interface WikiArticle {
  id: number;
  slug: string;
  title: string;
  summary: string;
  body_markdown?: string;
  difficulty: string;
  category: { id: number; slug: string; name: string; parent_id?: number | null };
  order_index?: number;
  tags: { slug: string; name: string }[];
  updated_at: string;
}

export interface WikiCategory {
  id: number;
  slug: string;
  name: string;
  parent_id: number | null;
  order_index: number;
  article_count: number;
  children: WikiCategory[];
}

export interface Project {
  id: number;
  name: string;
  slug: string;
  summary: string;
  description_markdown: string;
  repository_url: string;
  demo_url?: string | null;
  license_name: string;
  tech_stack: string[];
  status: PublicationStatus;
  is_featured: boolean;
  review_note?: string | null;
  submitted_at?: string | null;
  published_at?: string | null;
}

export interface Skill {
  slug: string;
  name: string;
  summary: string;
  version: string;
  license_name?: string | null;
  compatibility?: string | null;
  sha256: string;
}

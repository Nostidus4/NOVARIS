-- Q-SHIELD: snapshot workflow_update cho dashboard (JSON đã tính từ packages/*, không tính lại CVaR).
-- Chạy một lần trong Supabase Dashboard → SQL Editor → New query → Run.
-- Backend dùng SUPABASE_SECRET_KEY (bypass RLS). Không mở anon/public read.

create extension if not exists pgcrypto;

create table if not exists public.workflow_snapshots (
  id uuid primary key default gen_random_uuid(),
  run_key text not null unique,
  mode text not null,
  profile_id text not null,
  profile_status text not null,
  config_version text not null,
  stage_status jsonb not null default '{}'::jsonb,
  candidate_count integer not null default 0,
  payload jsonb not null,
  synced_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create index if not exists workflow_snapshots_profile_id_idx
  on public.workflow_snapshots (profile_id);

create index if not exists workflow_snapshots_synced_at_idx
  on public.workflow_snapshots (synced_at desc);

alter table public.workflow_snapshots enable row level security;

-- Không tạo policy cho anon/authenticated → chỉ service/secret role đọc/ghi được.
comment on table public.workflow_snapshots is
  'Serialized WorkflowSummaryDTO from artifact files; source of truth for compute remains packages/*.';

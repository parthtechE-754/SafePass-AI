-- ============================================================================
-- SafePass AI — Supabase Database Migration Schema
-- Copy and paste this script directly into your Supabase SQL Editor
-- (Dashboard -> SQL Editor -> New Query -> Run)
-- ============================================================================

-- 1. Enable UUID extension
create extension if not exists "uuid-ossp";

-- ── TABLE 1: trips (Corridor Route History & Safety Predictions) ───────────
create table if not exists public.trips (
    id uuid default gen_random_uuid() primary key,
    created_at timestamptz default timezone('utc'::text, now()) not null,
    origin_name text not null,
    origin_lat double precision not null,
    origin_lng double precision not null,
    dest_name text not null,
    dest_lat double precision not null,
    dest_lng double precision not null,
    corridor_name text not null,
    safety_score double precision default 5.0,
    avg_cri double precision default 3.0,
    distance_km double precision default 0.0,
    est_time_min integer default 0,
    danger_zones integer default 0,
    weather jsonb default '{}'::jsonb,
    user_id text default 'driver_anon'
);

-- Index for speedy queries by creation date
create index if not exists idx_trips_created_at on public.trips (created_at desc);

-- ── TABLE 2: hazard_reports (Crowdsourced Citizen & Driver Hazard Reports) ─
create table if not exists public.hazard_reports (
    id uuid default gen_random_uuid() primary key,
    created_at timestamptz default timezone('utc'::text, now()) not null,
    title text not null,
    hazard_type text default 'blackspot', -- 'blackspot', 'fog', 'waterlogging', 'unlit', 'pothole', 'accident'
    severity double precision default 5.0,
    lat double precision not null,
    lng double precision not null,
    highway text default 'National Highway',
    description text,
    reported_by text default 'Citizen Reporter',
    verified boolean default false
);

create index if not exists idx_hazard_created_at on public.hazard_reports (created_at desc);
create index if not exists idx_hazard_coords on public.hazard_reports (lat, lng);

-- ── TABLE 3: emergency_sos_logs (Emergency Dispatches: 112, 1033, 108) ─────
create table if not exists public.emergency_sos_logs (
    id uuid default gen_random_uuid() primary key,
    created_at timestamptz default timezone('utc'::text, now()) not null,
    user_lat double precision not null,
    user_lng double precision not null,
    service_dialed text not null, -- '112', '1033', '108'
    status text default 'DISPATCH_ALERT_TRIGGERED',
    notes text
);

create index if not exists idx_sos_created_at on public.emergency_sos_logs (created_at desc);

-- ── Row Level Security (RLS) ───────────────────────────────────────────────
-- Allow public insert & read for demonstration and client apps
alter table public.trips enable row level security;
alter table public.hazard_reports enable row level security;
alter table public.emergency_sos_logs enable row level security;

-- Policies for public anonymous read/write
create policy "Allow public read trips" on public.trips for select using (true);
create policy "Allow public insert trips" on public.trips for insert with check (true);

create policy "Allow public read hazards" on public.hazard_reports for select using (true);
create policy "Allow public insert hazards" on public.hazard_reports for insert with check (true);

create policy "Allow public read sos" on public.emergency_sos_logs for select using (true);
create policy "Allow public insert sos" on public.emergency_sos_logs for insert with check (true);

-- Insert sample community hazard report
insert into public.hazard_reports (title, hazard_type, severity, lat, lng, highway, description, reported_by, verified)
values
('Waterlogging Warning on NH-48', 'waterlogging', 7.5, 18.7512, 73.4123, 'NH-48 Pune Express', 'Monsoon runoff near Khopoli bypass sector. Reduced traction.', 'NHAI Patrol', true),
('Severe Dense Fog Stretch', 'fog', 8.0, 28.3245, 77.0123, 'NH-48 Delhi-Jaipur', 'Early morning low visibility corridor. Speed limit 40 km/h.', 'SafePass Auto-Sensor', true);

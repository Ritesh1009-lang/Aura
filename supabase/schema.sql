-- Run this entire file in Supabase Dashboard > SQL Editor.
-- It is safe to run more than once.
-- Credentials are stored only by Supabase Auth in auth.users. Never create a
-- password column in public.profiles.

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  username text not null,
  phone_country text,
  phone_number text,
  date_of_birth date,
  age smallint check (age >= 13 and age <= 130),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists profiles_username_lower_unique
on public.profiles (lower(username));

alter table public.profiles enable row level security;

drop policy if exists "Users can read their own profile" on public.profiles;
create policy "Users can read their own profile"
on public.profiles for select to authenticated
using ((select auth.uid()) = id);

drop policy if exists "Users can update their own profile" on public.profiles;
create policy "Users can update their own profile"
on public.profiles for update to authenticated
using ((select auth.uid()) = id)
with check ((select auth.uid()) = id);

-- This trigger creates the profile automatically after every Auth sign-up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (
    id, email, username, phone_country, phone_number, date_of_birth, age
  ) values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'username', split_part(new.email, '@', 1)),
    new.raw_user_meta_data ->> 'phone_country',
    new.raw_user_meta_data ->> 'phone_number',
    nullif(new.raw_user_meta_data ->> 'date_of_birth', '')::date,
    nullif(new.raw_user_meta_data ->> 'age', '')::smallint
  ) on conflict (id) do update set
    email = excluded.email,
    username = excluded.username,
    phone_country = excluded.phone_country,
    phone_number = excluded.phone_number,
    date_of_birth = excluded.date_of_birth,
    age = excluded.age,
    updated_at = now();
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

-- Backfill profiles for Auth users that were created before this trigger.
insert into public.profiles (id, email, username, phone_country, phone_number, date_of_birth, age)
select
  id,
  email,
  coalesce(raw_user_meta_data ->> 'username', split_part(email, '@', 1)),
  raw_user_meta_data ->> 'phone_country',
  raw_user_meta_data ->> 'phone_number',
  nullif(raw_user_meta_data ->> 'date_of_birth', '')::date,
  nullif(raw_user_meta_data ->> 'age', '')::smallint
from auth.users
on conflict (id) do nothing;

create table if not exists public.quiz_results (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  quiz_type text not null check (quiz_type in ('anxiety', 'depression', 'phone_addiction', 'fear')),
  score smallint not null check (score between 10 and 40),
  created_at timestamptz not null default now()
);

alter table public.quiz_results enable row level security;

drop policy if exists "Users can read their own quiz results" on public.quiz_results;
create policy "Users can read their own quiz results"
on public.quiz_results for select to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "Users can add their own quiz results" on public.quiz_results;
create policy "Users can add their own quiz results"
on public.quiz_results for insert to authenticated
with check ((select auth.uid()) = user_id);

create index if not exists quiz_results_user_created_at_idx
on public.quiz_results (user_id, created_at desc);

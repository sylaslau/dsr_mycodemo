-- Mycelly research database (Supabase): the 10 tables the app writes to.
-- Tables and column names match data/interim/extracted/*.csv exactly, in the same order
-- (checked by tests/test_supabase_schema.py). Text columns are text, numbers numeric.
-- stage, protocol, measure (fixed code lists that ship with the app) and growth_parameter have no table:
-- growers never send them; the rows carry only their codes (ST4, RUN, ...).
-- Changed 2026-11-10: container -> compartment (+ role); fermentation container_id -> vessel_id,
--   incubation_container_id -> container_id, + co2_ppm.
-- To rebuild the live project from older tables, run
--   MycoMaterials/md_library/cards/supabase-reset-and-schema-2026-11-10.sql (drops + this schema) instead.
-- The app (role anon) may only INSERT: it cannot read, change or delete anything.
-- Read the data in the dashboard (Table editor) or with the service key.

create table public.dataset (
  dataset_id text primary key,
  citation text,
  source_url text,
  license text,
  lab text,
  regime text,
  purpose text,
  status text,
  note text
);

create table public.sample (
  sample_id text primary key,
  dataset_id text,
  replicate_no numeric,
  n_specimens numeric,
  growth_outcome text,
  substrate_id text,
  fermentation_id text,
  initial_fill_weight_g numeric,
  notes text
);

create table public.fermentation (
  fermentation_id text primary key,
  genus text,
  species text,
  fibre_pct_wt numeric,
  water_pct_wt numeric,
  spawn_pct_wt numeric,
  water_pct_of_fibre numeric,
  vessel_id text,
  fill_height_mm numeric,
  container_id text,
  incubation_temp_c numeric,
  rh_pct numeric,
  co2_ppm numeric,
  total_growth_days numeric
);

create table public.substrate (
  substrate_id text primary key,
  plant_name text,
  plant_species text,
  particle_size_class numeric,
  particle_size_mm numeric,
  pre_treatment text,
  sterilisation text,
  cn_estimate numeric,
  cn_confidence text,
  component_1 text,
  pct_dry_1 numeric,
  component_2 text,
  pct_dry_2 numeric,
  component_3 text,
  pct_dry_3 numeric
);

-- role = vessel (holds the substrate), container (holds vessels) or residence (room, tent, box around them).
create table public.compartment (
  compartment_id text primary key,
  role text,
  container_type text,
  container_shape text,
  inner_diameter_mm numeric,
  inner_length_mm numeric,
  inner_width_mm numeric,
  inner_height_mm numeric,
  closure text,
  notes text
);

-- The planned steps of a fermentation; stage_id and protocol_id are codes from stage.csv and protocol.csv.
create table public.process (
  fermentation_id text,
  step_no numeric,
  stage_id text,
  protocol_id text,
  vessel_id text,
  container_id text,
  residence_id text,
  day_start numeric,
  duration_days numeric,
  duration_h numeric,
  temp_c numeric,
  rh_pct numeric,
  primary key (fermentation_id, step_no)
);

-- Log during growth: one row per sample, day and measure.
create table public.reading (
  dataset_id text,
  sample_id text,
  measurement_type text,
  stage_id text,
  day numeric,
  measure_id text,
  value numeric
);

-- Results per sample (e.g. biological_efficiency per flush, day = flush day).
create table public.outcome (
  dataset_id text,
  sample_id text,
  measurement_type text,
  measure_id text,
  day numeric,
  value numeric
);

create table public.image (
  image_id text primary key,
  dataset_id text,
  sample_id text,
  image_type text,
  file_path text,
  acquired_date text,
  start_date_in_filename text,
  day_of_growth numeric,
  segment numeric,
  hour numeric
);

create table public.flag (
  dataset_id text,
  table_name text,
  key_value text,
  flag_code text,
  note text
);

-- 3. Lock every table: the app may only add rows.
alter table public.dataset enable row level security;
alter table public.sample enable row level security;
alter table public.fermentation enable row level security;
alter table public.substrate enable row level security;
alter table public.compartment enable row level security;
alter table public.process enable row level security;
alter table public.reading enable row level security;
alter table public.outcome enable row level security;
alter table public.image enable row level security;
alter table public.flag enable row level security;

grant insert on public.dataset, public.sample, public.fermentation, public.substrate, public.compartment,
  public.process, public.reading, public.outcome, public.image, public.flag to anon;

create policy "anon insert only" on public.dataset for insert to anon with check (true);
create policy "anon insert only" on public.sample for insert to anon with check (true);
create policy "anon insert only" on public.fermentation for insert to anon with check (true);
create policy "anon insert only" on public.substrate for insert to anon with check (true);
create policy "anon insert only" on public.compartment for insert to anon with check (true);
create policy "anon insert only" on public.process for insert to anon with check (true);
create policy "anon insert only" on public.reading for insert to anon with check (true);
create policy "anon insert only" on public.outcome for insert to anon with check (true);
create policy "anon insert only" on public.image for insert to anon with check (true);
create policy "anon insert only" on public.flag for insert to anon with check (true);

-- Photos: private bucket, anon may upload (INSERT) only; no listing, download, overwrite or delete.
insert into storage.buckets (id, name, public) values ('photos', 'photos', false);
create policy "anon upload photos only" on storage.objects for insert to anon
  with check (bucket_id = 'photos');

-- Deleting one contributor's data (a test send, or a deletion request): replace u-xxxxxx, remove the "-- " and run.
-- delete from public.flag where dataset_id = 'u-xxxxxx';
-- delete from public.image where dataset_id = 'u-xxxxxx';
-- delete from public.outcome where dataset_id = 'u-xxxxxx';
-- delete from public.reading where dataset_id = 'u-xxxxxx';
-- delete from public.sample where dataset_id = 'u-xxxxxx';
-- delete from public.process where fermentation_id like 'u-xxxxxx-%';
-- delete from public.fermentation where fermentation_id like 'u-xxxxxx-%';
-- delete from public.substrate where substrate_id like 'u-xxxxxx-%';
-- delete from public.compartment where compartment_id like 'u-xxxxxx-%';
-- delete from public.dataset where dataset_id = 'u-xxxxxx';
-- Photos: Storage > photos > folder u-xxxxxx > delete.

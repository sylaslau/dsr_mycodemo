-- Mycelly research database (Supabase). Paste into the Supabase SQL editor and run once.
-- Tables and column names match data/interim/extracted/*.csv exactly (no extra columns).
-- Text columns are text, numbers numeric.
-- Changed 2026-11-06: measurement replaced by reading + outcome, fermentation step columns moved to process.
-- On a database made from the older file, first drop the old table and columns (old test rows go with them):
--   drop table public.measurement;
--   alter table public.fermentation drop column phase1_days, drop column phase2_days, drop column phase3_days,
--     drop column in_process_treatment, drop column post_treatment, drop column post_treatment_temp_c,
--     drop column post_treatment_time_h;
--   then run only the create table blocks for process, reading and outcome below.
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
alter table public.dataset enable row level security;
grant insert on public.dataset to anon;
create policy "anon insert only" on public.dataset for insert to anon with check (true);

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
alter table public.sample enable row level security;
grant insert on public.sample to anon;
create policy "anon insert only" on public.sample for insert to anon with check (true);

create table public.fermentation (
  fermentation_id text primary key,
  genus text,
  species text,
  fibre_pct_wt numeric,
  water_pct_wt numeric,
  spawn_pct_wt numeric,
  water_pct_of_fibre numeric,
  container_id text,
  fill_height_mm numeric,
  incubation_container_id text,
  incubation_temp_c numeric,
  rh_pct numeric,
  total_growth_days numeric
);
alter table public.fermentation enable row level security;
grant insert on public.fermentation to anon;
create policy "anon insert only" on public.fermentation for insert to anon with check (true);

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
alter table public.substrate enable row level security;
grant insert on public.substrate to anon;
create policy "anon insert only" on public.substrate for insert to anon with check (true);

create table public.container (
  container_id text primary key,
  container_type text,
  container_shape text,
  inner_diameter_mm numeric,
  inner_length_mm numeric,
  inner_width_mm numeric,
  inner_height_mm numeric,
  closure text,
  notes text
);
alter table public.container enable row level security;
grant insert on public.container to anon;
create policy "anon insert only" on public.container for insert to anon with check (true);

-- The planned steps of a fermentation (process.csv, "the notebook"); stage_id and protocol_id are codes from
-- stage.csv and protocol.csv (e.g. ST4 RUN = main spawn run).
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
alter table public.process enable row level security;
grant insert on public.process to anon;
create policy "anon insert only" on public.process for insert to anon with check (true);

-- Log during growth (reading.csv): one row per sample, day and measure (colonisation_score, surface_colonised_pct).
create table public.reading (
  dataset_id text,
  sample_id text,
  measurement_type text,
  stage_id text,
  day numeric,
  measure_id text,
  value numeric
);
alter table public.reading enable row level security;
grant insert on public.reading to anon;
create policy "anon insert only" on public.reading for insert to anon with check (true);

-- Results per sample (outcome.csv): biological_efficiency per flush (day = flush day), strength, density.
create table public.outcome (
  dataset_id text,
  sample_id text,
  measurement_type text,
  measure_id text,
  day numeric,
  value numeric
);
alter table public.outcome enable row level security;
grant insert on public.outcome to anon;
create policy "anon insert only" on public.outcome for insert to anon with check (true);

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
alter table public.image enable row level security;
grant insert on public.image to anon;
create policy "anon insert only" on public.image for insert to anon with check (true);

create table public.flag (
  dataset_id text,
  table_name text,
  key_value text,
  flag_code text,
  note text
);
alter table public.flag enable row level security;
grant insert on public.flag to anon;
create policy "anon insert only" on public.flag for insert to anon with check (true);

-- Photos: private bucket, anon may upload (INSERT) only; no listing, download, overwrite or delete.
insert into storage.buckets (id, name, public) values ('photos', 'photos', false);
create policy "anon upload photos only" on storage.objects for insert to anon
  with check (bucket_id = 'photos');

-- Deleting one contributor's data (e.g. a test send, or a deletion request): replace u-xxxxxx and run.
-- Tables without a primary key (reading, outcome, flag) cannot be deleted row by row in the Table editor.
-- delete from public.flag where dataset_id = 'u-xxxxxx';
-- delete from public.image where dataset_id = 'u-xxxxxx';
-- delete from public.outcome where dataset_id = 'u-xxxxxx';
-- delete from public.reading where dataset_id = 'u-xxxxxx';
-- delete from public.sample where dataset_id = 'u-xxxxxx';
-- delete from public.process where fermentation_id like 'u-xxxxxx-%';
-- delete from public.fermentation where fermentation_id like 'u-xxxxxx-%';
-- delete from public.substrate where substrate_id like 'u-xxxxxx-%';
-- delete from public.container where container_id like 'u-xxxxxx-%';
-- delete from public.dataset where dataset_id = 'u-xxxxxx';
-- Photos: Storage > photos > folder u-xxxxxx > delete.

-- FINN initial schema
create extension if not exists pg_trgm;

create table companies (
  symbol text primary key,
  name text not null,
  bse_code text,
  isin text,
  sector text,
  is_financial boolean not null default false,
  ir_url text
);

create table portfolios (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  window_hours int not null default 24,
  vol_mult numeric not null default 2,
  price_pct numeric not null default 5,
  created_at timestamptz not null default now()
);

create table portfolio_holdings (
  portfolio_id uuid references portfolios(id) on delete cascade,
  symbol text references companies(symbol),
  vol_mult numeric,
  price_pct numeric,
  primary key (portfolio_id, symbol)
);

create table documents (
  sha256 text primary key,
  symbol text references companies(symbol),
  kind text not null check (kind in ('results','transcript','annual_report','filing','other')),
  source_url text,
  storage_path text,
  n_pages int,
  fetched_at timestamptz not null default now()
);

create table doc_pages (
  sha256 text references documents(sha256) on delete cascade,
  page int not null,
  text text not null default '',
  method text not null default 'pdfplumber' check (method in ('pdfplumber','tesseract','gemini')),
  tsv tsvector generated always as (to_tsvector('english', text)) stored,
  primary key (sha256, page)
);
create index doc_pages_tsv_idx on doc_pages using gin (tsv);

create table filings (
  id text primary key,
  symbol text references companies(symbol),
  headline text not null,
  category text,
  classified_by text check (classified_by in ('rule','llm8b')),
  materiality numeric,
  never_collapse boolean not null default false,
  summary text,
  doc_sha256 text references documents(sha256),
  published_at timestamptz not null,
  reviewed boolean not null default false
);
create index filings_symbol_time on filings (symbol, published_at desc);

create table results (
  id uuid primary key default gen_random_uuid(),
  symbol text references companies(symbol),
  period text not null,
  doc_sha256 text references documents(sha256),
  basis text check (basis in ('consolidated','standalone')),
  parsed jsonb,
  checks jsonb,
  status text not null check (status in ('ok','see_pdf','unsupported')),
  flags jsonb not null default '[]',
  unique (symbol, period, doc_sha256)
);

create table guidance (
  id uuid primary key default gen_random_uuid(),
  symbol text references companies(symbol),
  doc_sha256 text references documents(sha256),
  page int not null,
  quarter text not null,
  metric text,
  target jsonb,
  quote text not null,
  prompt_version text not null
);

create table actuals (
  id uuid primary key default gen_random_uuid(),
  symbol text references companies(symbol),
  period text not null,
  metric text not null,
  value numeric,
  results_id uuid references results(id),
  doc_sha256 text references documents(sha256),
  page int
);

create table promise_matches (
  guidance_id uuid references guidance(id) on delete cascade,
  actual_id uuid references actuals(id),
  status text not null check (status in ('Delivered','Missed','Partly','Vague','Not yet due','No comparable actual')),
  detail jsonb,
  primary key (guidance_id)
);

create table prices (
  symbol text references companies(symbol),
  d date not null,
  close numeric,
  volume bigint,
  primary key (symbol, d)
);

create table alerts (
  id uuid primary key default gen_random_uuid(),
  symbol text references companies(symbol),
  d date not null,
  kind text not null check (kind in ('volume','price','filing')),
  detail jsonb,
  cause_label text check (cause_label in ('No related filing found','Related filing found, cause unconfirmed')),
  created_at timestamptz not null default now(),
  unique (symbol, d, kind)
);

create table jobs (
  id uuid primary key default gen_random_uuid(),
  kind text not null,
  key text,
  status text not null default 'queued' check (status in ('queued','running','done','failed')),
  result jsonb,
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index jobs_key_idx on jobs (kind, key);

create table llm_cache (
  key text primary key,          -- sha256(model + prompt_version + input)
  model text not null,
  prompt_version text not null,
  response jsonb not null,
  created_at timestamptz not null default now()
);

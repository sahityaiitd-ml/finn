-- M1: fields needed by ingestion
alter table companies add column if not exists grp text not null default 'portfolio'
  check (grp in ('portfolio','research'));
alter table documents add column if not exists period text;          -- quarter end, 'YYYY-MM'
alter table filings add column if not exists url text;
alter table filings add column if not exists description text;

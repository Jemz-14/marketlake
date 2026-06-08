/* ============================================================================
   Synapse SERVERLESS SQL — serving views over the gold Parquet in ADLS Gen2.

   Run against the workspace's serverless endpoint
   (<workspace>-ondemand.sql.azuresynapse.net). The serverless pool reads files
   in storage, authenticating as the workspace's MANAGED IDENTITY (granted
   Storage Blob Data Reader by Terraform) — no keys or SAS in the SQL.

   serving/setup_synapse.py runs this end to end (it creates the database and a
   master key first, then executes the statements below).
   ============================================================================ */

-- Run inside the serving database (created by setup_synapse.py):
--   USE marketlake_serving;

-- Managed-identity credential + a data source rooted at the `data` filesystem.
CREATE DATABASE SCOPED CREDENTIAL synapse_msi WITH IDENTITY = 'Managed Identity';

CREATE EXTERNAL DATA SOURCE gold_lake WITH (
    LOCATION   = 'https://<STORAGE_ACCOUNT>.dfs.core.windows.net/data',
    CREDENTIAL = synapse_msi
);

-- One view per gold table. OPENROWSET infers the schema from the Parquet, so
-- there's no column list to maintain.
CREATE OR ALTER VIEW dbo.dim_date AS
SELECT * FROM OPENROWSET(BULK 'gold/dim_date/', DATA_SOURCE = 'gold_lake', FORMAT = 'PARQUET') AS r;

CREATE OR ALTER VIEW dbo.dim_security AS
SELECT * FROM OPENROWSET(BULK 'gold/dim_security/', DATA_SOURCE = 'gold_lake', FORMAT = 'PARQUET') AS r;

CREATE OR ALTER VIEW dbo.dim_sector AS
SELECT * FROM OPENROWSET(BULK 'gold/dim_sector/', DATA_SOURCE = 'gold_lake', FORMAT = 'PARQUET') AS r;

CREATE OR ALTER VIEW dbo.fact_daily_price AS
SELECT * FROM OPENROWSET(BULK 'gold/fact_daily_price/', DATA_SOURCE = 'gold_lake', FORMAT = 'PARQUET') AS r;

CREATE OR ALTER VIEW dbo.fact_price_indicators AS
SELECT * FROM OPENROWSET(BULK 'gold/fact_price_indicators/', DATA_SOURCE = 'gold_lake', FORMAT = 'PARQUET') AS r;

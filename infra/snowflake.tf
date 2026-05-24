resource "snowflake_database" "alt_db" {
  name    = "ALT_DB"
  comment = "Database for Alpine Lambda Trade (Batch and Speed Layers)"
}

resource "snowflake_schema" "alt_bronze" {
  database = snowflake_database.alt_db.name
  name     = "BRONZE"
  comment  = "Schema for raw data ingestion (S3 / Real-time)"
}

resource "snowflake_schema" "alt_silver" {
  database = snowflake_database.alt_db.name
  name     = "SILVER"
  comment  = "Cleansed and deduplicated data (dbt)"
}

resource "snowflake_schema" "alt_gold" {
  database = snowflake_database.alt_db.name
  name     = "GOLD"
  comment  = "Business views and aggregations (dbt)"
}

resource "snowflake_warehouse" "alt_wh" {
  name                = "ALT_WH"
  warehouse_size      = "X-SMALL"
  auto_suspend        = 60 # Règle métiers 6.C: Cost control
  auto_resume         = true
  initially_suspended = true
}

resource "snowflake_grant_privileges_to_account_role" "wh_grant" {
  privileges        = ["USAGE", "OPERATE"]
  account_role_name = snowflake_role.alt_engineer.name
  on_account_object {
    object_type = "WAREHOUSE"
    object_name = snowflake_warehouse.alt_wh.name
  }
}

resource "snowflake_role" "alt_engineer" {
  name    = "ALT_ENGINEER"
  comment = "Data Engineer role for interacting with ALT DB"
}

resource "snowflake_grant_account_role" "engineer_grant" {
  role_name = snowflake_role.alt_engineer.name
  user_name = upper(var.snowflake_user)
}

resource "snowflake_grant_privileges_to_account_role" "db_grant" {
  privileges        = ["USAGE", "CREATE SCHEMA", "MODIFY"]
  account_role_name = snowflake_role.alt_engineer.name
  on_account_object {
    object_type = "DATABASE"
    object_name = snowflake_database.alt_db.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "schema_grant" {
  privileges        = ["USAGE", "CREATE TABLE", "CREATE VIEW", "MODIFY", "MONITOR"]
  account_role_name = snowflake_role.alt_engineer.name
  on_schema {
    all_schemas_in_database = snowflake_database.alt_db.name
  }
}

# Explicit grants on specific schemas to ensure dbt can operate
resource "snowflake_grant_privileges_to_account_role" "medallion_grants" {
  for_each = toset([
    snowflake_schema.alt_bronze.name,
    snowflake_schema.alt_silver.name,
    snowflake_schema.alt_gold.name
  ])
  
  privileges        = ["USAGE", "CREATE TABLE", "CREATE VIEW", "MODIFY", "MONITOR"]
  account_role_name = snowflake_role.alt_engineer.name
  on_schema {
    schema_name = "\"${snowflake_database.alt_db.name}\".\"${each.value}\""
  }
}

resource "snowflake_grant_privileges_to_account_role" "future_schema_grant" {
  privileges        = ["USAGE", "CREATE TABLE", "CREATE VIEW", "MODIFY", "MONITOR"]
  account_role_name = snowflake_role.alt_engineer.name
  on_schema {
    future_schemas_in_database = snowflake_database.alt_db.name
  }
}

# Storage Integration
resource "snowflake_storage_integration" "alt_s3_integration" {
  name    = "ALT_S3_INTEGRATION"
  comment = "Integration with AWS S3 alt-raw-data bucket"
  type    = "EXTERNAL_STAGE"

  enabled = true

  storage_provider         = "S3"
  storage_aws_role_arn     = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/alt-snowflake-s3-role"
  storage_allowed_locations = ["s3://alt-raw-data-${data.aws_caller_identity.current.account_id}/"]
}

# ==============================================================================
# OUTPUTS (Pour l'étape 2 du setup : maj du Trust IAM Role sur AWS)
# ==============================================================================

output "snowflake_storage_aws_iam_user_arn" {
  value       = snowflake_storage_integration.alt_s3_integration.storage_aws_iam_user_arn
  description = "The Snowflake AWS IAM User ARN. À copier dans 'Principal' -> 'AWS' de la Trust Policy de alt-snowflake-s3-role."
}

output "snowflake_storage_aws_external_id" {
  value       = snowflake_storage_integration.alt_s3_integration.storage_aws_external_id
  description = "The Snowflake External ID. À copier dans sts:ExternalId de la Trust Policy de alt-snowflake-s3-role."
}

# ==============================================================================
# SPRINT 3: Snowpipe & Batch Ingestion
# ==============================================================================

resource "snowflake_table" "alt_raw_trade" {
  database = snowflake_database.alt_db.name
  schema   = snowflake_schema.alt_bronze.name
  name     = "RAW_TRADE"
  comment  = "Raw Parquet ingestion table"

  column {
    name = "PAYLOAD"
    type = "VARIANT"
  }
}

resource "snowflake_file_format" "alt_parquet_format" {
  database    = snowflake_database.alt_db.name
  schema      = snowflake_schema.alt_bronze.name
  name        = "ALT_PARQUET_FORMAT"
  format_type = "PARQUET"
  compression = "AUTO"
}

resource "snowflake_stage" "alt_raw_stage" {
  name                = "ALT_RAW_STAGE"
  url                 = "s3://alt-raw-data-${data.aws_caller_identity.current.account_id}/ticker/"
  database            = snowflake_database.alt_db.name
  schema              = snowflake_schema.alt_bronze.name
  storage_integration = snowflake_storage_integration.alt_s3_integration.name
  file_format         = "FORMAT_NAME = ${snowflake_database.alt_db.name}.${snowflake_schema.alt_bronze.name}.${snowflake_file_format.alt_parquet_format.name}"
}

resource "snowflake_pipe" "alt_snowpipe" {
  database       = snowflake_database.alt_db.name
  schema         = snowflake_schema.alt_bronze.name
  name           = "ALT_SNOWPIPE"
  auto_ingest    = true
  copy_statement = "COPY INTO ${snowflake_database.alt_db.name}.${snowflake_schema.alt_bronze.name}.${snowflake_table.alt_raw_trade.name} (PAYLOAD) FROM (SELECT $1 FROM @${snowflake_database.alt_db.name}.${snowflake_schema.alt_bronze.name}.${snowflake_stage.alt_raw_stage.name})"
  
  depends_on = [
    snowflake_table.alt_raw_trade,
    snowflake_stage.alt_raw_stage
  ]
}

output "snowflake_sqs_arn" {
  value       = snowflake_pipe.alt_snowpipe.notification_channel
  description = "SQS auto-generated by Snowflake for S3 Event Notifications."
}

# ==============================================================================
# SPRINT 4: Speed Pipeline & Real-Time Lambda Sink
# ==============================================================================

resource "snowflake_table" "bronze_realtime" {
  database = snowflake_database.alt_db.name
  schema   = snowflake_schema.alt_bronze.name
  name     = "REALTIME_TRADE"
  comment  = "Real-time volatile records populated instantaneously by AWS Lambda"

  column {
    name = "TRADE_ID"
    type = "VARCHAR(255)"
  }
  
  column {
    name = "SYMBOL"
    type = "VARCHAR(50)"
  }

  column {
    name = "PRICE"
    type = "FLOAT"
  }
  
  column {
    name = "EMA"
    type = "FLOAT"
  }
  
  column {
    name = "SPIKE_DETECTED"
    type = "BOOLEAN"
  }

  column {
    name = "UPPER_BAND"
    type = "FLOAT"
  }

  column {
    name = "LOWER_BAND"
    type = "FLOAT"
  }

  column {
    name = "TRADE_TIMESTAMP"
    type = "TIMESTAMP_NTZ(9)"
  }
}

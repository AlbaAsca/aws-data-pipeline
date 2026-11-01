output "lake_bucket" {
  value = aws_s3_bucket.lake.id
}

output "ingest_function" {
  value = aws_lambda_function.ingest.function_name
}

output "raw_glob" {
  description = "Ruta que lee dbt (RAW_GLOB)"
  value       = "s3://${aws_s3_bucket.lake.id}/${var.raw_prefix}/**/*.parquet"
}

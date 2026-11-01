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

output "alerts_topic" {
  value = aws_sns_topic.alerts.arn
}

output "ingest_dlq" {
  value = aws_sqs_queue.ingest_dlq.url
}

output "dbt_project" {
  value = var.enable_scheduled_dbt ? aws_codebuild_project.dbt[0].name : null
}

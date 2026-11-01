variable "project" {
  type    = string
  default = "weather-pipeline"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "region" {
  description = "eu-south-2 = España (Aragón)"
  type        = string
  default     = "eu-south-2"
}

variable "raw_prefix" {
  type    = string
  default = "raw/weather"
}

variable "schedule" {
  description = "Cada día a las 06:00 UTC, con el día anterior ya cerrado"
  type        = string
  default     = "cron(0 6 * * ? *)"
}

variable "lambda_zip" {
  description = "Zip generado por scripts/build_lambda.py"
  type        = string
  default     = "../../dist/ingest_lambda.zip"
}

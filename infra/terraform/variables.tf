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

variable "cities" {
  description = "Ciudades a ingerir; deben existir también en transform/seeds/cities.csv"
  type = list(object({
    city = string
    lat  = number
    lon  = number
  }))
  default = [
    { city = "madrid", lat = 40.4168, lon = -3.7038 },
    { city = "barcelona", lat = 41.3874, lon = 2.1686 },
    { city = "valencia", lat = 39.4699, lon = -0.3763 },
    { city = "sevilla", lat = 37.3891, lon = -5.9845 },
    { city = "bilbao", lat = 43.2630, lon = -2.9350 },
    { city = "zaragoza", lat = 41.6488, lon = -0.8891 },
  ]
}

variable "alert_email" {
  description = "Email para las alarmas (vacío = sin suscripción)"
  type        = string
  default     = ""
}

variable "enable_scheduled_dbt" {
  description = "dbt diario en CodeBuild. Desactivado por defecto: LocalStack Community no tiene CodeBuild"
  type        = bool
  default     = false
}

variable "dbt_schedule" {
  type    = string
  default = "cron(0 7 * * ? *)"
}

variable "repo_url" {
  description = "Repositorio público que clona CodeBuild"
  type        = string
  default     = "https://github.com/AlbaAsca/aws-data-pipeline.git"
}

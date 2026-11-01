# ---------- dbt diario en CodeBuild (opcional) ----------
# CodeBuild clona el repo, ejecuta `dbt build` contra S3 y sube warehouse.duckdb a warehouse/.
# Con general1.small y ~3 min al día entra en los 100 minutos gratuitos al mes de CodeBuild.

locals {
  dbt_count = var.enable_scheduled_dbt ? 1 : 0
}

data "aws_iam_policy_document" "assume_codebuild" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["codebuild.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "dbt" {
  count              = local.dbt_count
  name               = "${local.name}-dbt"
  assume_role_policy = data.aws_iam_policy_document.assume_codebuild.json
}

# Lee raw/, escribe solo warehouse/ y sus logs.
data "aws_iam_policy_document" "dbt" {
  statement {
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.lake.arn]
  }
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.lake.arn}/${var.raw_prefix}/*"]
  }
  statement {
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.lake.arn}/warehouse/*"]
  }
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/codebuild/${local.name}-dbt:*"]
  }
}

resource "aws_iam_role_policy" "dbt" {
  count  = local.dbt_count
  role   = aws_iam_role.dbt[0].id
  policy = data.aws_iam_policy_document.dbt.json
}

resource "aws_cloudwatch_log_group" "dbt" {
  count             = local.dbt_count
  name              = "/aws/codebuild/${local.name}-dbt"
  retention_in_days = 14
}

resource "aws_codebuild_project" "dbt" {
  count         = local.dbt_count
  name          = "${local.name}-dbt"
  description   = "dbt build diario sobre el Parquet de S3"
  service_role  = aws_iam_role.dbt[0].arn
  build_timeout = 15

  source {
    type      = "NO_SOURCE" # clona el repo público en el buildspec: sin conexión OAuth con GitHub
    buildspec = templatefile("${path.module}/buildspec-dbt.yml", { repo_url = var.repo_url })
  }

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type = "BUILD_GENERAL1_SMALL"
    image        = "aws/codebuild/amazonlinux-x86_64-standard:5.0"
    type         = "LINUX_CONTAINER"

    environment_variable {
      name  = "LAKE_BUCKET"
      value = aws_s3_bucket.lake.id
    }
    environment_variable {
      name  = "RAW_GLOB"
      value = "s3://${aws_s3_bucket.lake.id}/${var.raw_prefix}/**/*.parquet"
    }
    environment_variable {
      name  = "S3_ENDPOINT"
      value = "s3.${var.region}.amazonaws.com"
    }
  }

  logs_config {
    cloudwatch_logs {
      group_name = aws_cloudwatch_log_group.dbt[0].name
    }
  }
}

data "aws_iam_policy_document" "assume_events" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "events_dbt" {
  count              = local.dbt_count
  name               = "${local.name}-events-dbt"
  assume_role_policy = data.aws_iam_policy_document.assume_events.json
}

resource "aws_iam_role_policy" "events_dbt" {
  count = local.dbt_count
  role  = aws_iam_role.events_dbt[0].id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "codebuild:StartBuild", Resource = aws_codebuild_project.dbt[0].arn }]
  })
}

resource "aws_cloudwatch_event_rule" "dbt" {
  count               = local.dbt_count
  name                = "${local.name}-dbt-daily"
  description         = "dbt build una hora después de la ingesta"
  schedule_expression = var.dbt_schedule
}

resource "aws_cloudwatch_event_target" "dbt" {
  count    = local.dbt_count
  rule     = aws_cloudwatch_event_rule.dbt[0].name
  arn      = aws_codebuild_project.dbt[0].arn
  role_arn = aws_iam_role.events_dbt[0].arn
}

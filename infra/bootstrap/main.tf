# Se aplica UNA vez, a mano, con credenciales de administración (p. ej. desde CloudShell).
# Crea lo que el CI necesita para desplegar sin claves guardadas:
#   - el proveedor OIDC de GitHub y un rol que solo puede asumir este repo (entorno "aws"),
#   - un bucket para el estado remoto de Terraform (con bloqueo nativo de S3).

terraform {
  required_version = ">= 1.10" # use_lockfile en el backend S3
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.90"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = var.project, ManagedBy = "terraform", Stack = "bootstrap" }
  }
}

variable "region" {
  type    = string
  default = "eu-west-1"
}

variable "project" {
  type    = string
  default = "weather-pipeline"
}

variable "github_repo" {
  type    = string
  default = "AlbaAsca/aws-data-pipeline"
}

data "aws_caller_identity" "current" {}

locals {
  account = data.aws_caller_identity.current.account_id
  prefix  = var.project
}

# ---------- Estado remoto ----------

resource "aws_s3_bucket" "state" {
  bucket        = "${local.prefix}-tfstate-${local.account}"
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled" # recuperar un estado anterior si algo sale mal
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ---------- GitHub OIDC ----------

resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

data "aws_iam_policy_document" "trust_github" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    # Solo jobs de este repo que usen el entorno "aws" de GitHub (que puede exigir aprobación).
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:environment:aws"]
    }
  }
}

resource "aws_iam_role" "deploy" {
  name                 = "${local.prefix}-github-deploy"
  assume_role_policy   = data.aws_iam_policy_document.trust_github.json
  max_session_duration = 3600
}

# Permisos acotados a los recursos con prefijo del proyecto: no puede tocar nada más de la cuenta.
data "aws_iam_policy_document" "deploy" {
  statement {
    sid       = "Identity"
    actions   = ["sts:GetCallerIdentity"]
    resources = ["*"]
  }
  statement {
    sid       = "State"
    actions   = ["s3:ListBucket", "s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = [aws_s3_bucket.state.arn, "${aws_s3_bucket.state.arn}/*"]
  }
  statement {
    sid       = "Lake"
    actions   = ["s3:*"]
    resources = ["arn:aws:s3:::${local.prefix}-*-lake-${local.account}", "arn:aws:s3:::${local.prefix}-*-lake-${local.account}/*"]
  }
  statement {
    sid       = "Lambda"
    actions   = ["lambda:*"]
    resources = ["arn:aws:lambda:${var.region}:${local.account}:function:${local.prefix}-*"]
  }
  statement {
    sid = "Roles"
    actions = [
      "iam:CreateRole", "iam:DeleteRole", "iam:GetRole", "iam:UpdateRole", "iam:TagRole", "iam:UntagRole",
      "iam:PutRolePolicy", "iam:GetRolePolicy", "iam:DeleteRolePolicy", "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies", "iam:ListInstanceProfilesForRole", "iam:UpdateAssumeRolePolicy", "iam:PassRole",
    ]
    resources = ["arn:aws:iam::${local.account}:role/${local.prefix}-*"]
  }
  statement {
    sid     = "Logs"
    actions = ["logs:*"]
    resources = [
      "arn:aws:logs:${var.region}:${local.account}:log-group:/aws/lambda/${local.prefix}-*",
      "arn:aws:logs:${var.region}:${local.account}:log-group:/aws/codebuild/${local.prefix}-*",
    ]
  }
  statement {
    sid       = "Describe"
    actions   = ["logs:DescribeLogGroups", "cloudwatch:DescribeAlarms", "ssm:DescribeParameters"]
    resources = ["*"]
  }
  statement {
    sid       = "Events"
    actions   = ["events:*"]
    resources = ["arn:aws:events:${var.region}:${local.account}:rule/${local.prefix}-*"]
  }
  statement {
    sid     = "Alerts"
    actions = ["sns:*", "sqs:*", "cloudwatch:*"]
    resources = [
      "arn:aws:sns:${var.region}:${local.account}:${local.prefix}-*",
      "arn:aws:sqs:${var.region}:${local.account}:${local.prefix}-*",
      "arn:aws:cloudwatch:${var.region}:${local.account}:alarm:${local.prefix}-*",
    ]
  }
  statement {
    sid       = "Config"
    actions   = ["ssm:*"]
    resources = ["arn:aws:ssm:${var.region}:${local.account}:parameter/${local.prefix}/*"]
  }
  statement {
    sid       = "Dbt"
    actions   = ["codebuild:*"]
    resources = ["arn:aws:codebuild:${var.region}:${local.account}:project/${local.prefix}-*"]
  }
}

resource "aws_iam_role_policy" "deploy" {
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.deploy.json
}

output "deploy_role_arn" {
  value = aws_iam_role.deploy.arn
}

output "state_bucket" {
  value = aws_s3_bucket.state.id
}

# El estado del bootstrap vive en el bucket que él mismo crea (migrado tras el primer apply):
#   terraform init -backend-config=bucket=<state_bucket> -backend-config=key=bootstrap/terraform.tfstate \
#     -backend-config=region=eu-west-1 -backend-config=use_lockfile=true
# El primer apply en una cuenta nueva se hace con `terraform init -backend=false` y estado local,
# y después `terraform init -migrate-state` con la configuración de arriba.
terraform {
  backend "s3" {}
}

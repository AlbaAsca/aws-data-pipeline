# El estado del bootstrap vive en el bucket que él mismo crea (migrado tras el primer apply):
#   terraform init -backend-config=bucket=<state_bucket> -backend-config=key=bootstrap/terraform.tfstate \
#     -backend-config=region=eu-west-1 -backend-config=use_lockfile=true
# En una cuenta nueva el bucket aún no existe: primer apply con estado local creando
# backend_override.tf con `terraform { backend "local" {} }`; luego se borra ese fichero y
# `terraform init -migrate-state` con la configuración de arriba.
terraform {
  backend "s3" {}
}

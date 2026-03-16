# Define the directory containing the Docker image and calculate its SHA-256 hash for triggering redeployments
locals {
  lambda_dir     = abspath("${path.root}/../../lambdas/backend")
  lambda_files   = fileset(local.lambda_dir, "**")
  lambda_dir_sha = sha1(join("", [for f in local.lambda_files : filesha1("${local.lambda_dir}/${f}")]))
}

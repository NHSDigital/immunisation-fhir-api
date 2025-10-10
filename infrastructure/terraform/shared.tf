# Define locals for shared lambdas
locals {
  shared_dir        = abspath("${path.root}/../lambdas/shared")

  shared_files      = fileset(local.shared_dir, "**")

  shared_dir_sha    = sha1(join("", [for f in local.shared_files : filesha1("${local.shared_dir}/${f}")]))
}

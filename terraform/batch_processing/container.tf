locals {
    batch_source = abspath("${path.root}/../backend")
    path_include  = ["**"]
    path_exclude  = ["**/__pycache__/**"]
    files_include = setunion([for f in local.path_include : fileset(local.batch_source, f)]...)
    files_exclude = setunion([for f in local.path_exclude : fileset(local.batch_source, f)]...)
    files         = sort(setsubtract(local.files_include, local.files_exclude))

    dir_sha = sha1(join("", [for f in local.files : filesha1("${local.batch_source}/${f}")]))
}

module "docker_image" {
    source = "terraform-aws-modules/lambda/aws//modules/docker-build"

    docker_file_path = "batch.Dockerfile"
    create_ecr_repo           = false
    ecr_repo                  = aws_ecr_repository.batch_processing_repository.name
    ecr_repo_lifecycle_policy = jsonencode({
        "rules" : [
            {
                "rulePriority" : 1,
                "description" : "Keep only the last 2 images",
                "selection" : {
                    "tagStatus" : "any",
                    "countType" : "imageCountMoreThan",
                    "countNumber" : 2
                },
                "action" : {
                    "type" : "expire"
                }
            }
        ]
    })

    platform      = "linux/amd64"
    use_image_tag = false
    source_path   = local.batch_source
    triggers      = {
        dir_sha = local.dir_sha
    }
}


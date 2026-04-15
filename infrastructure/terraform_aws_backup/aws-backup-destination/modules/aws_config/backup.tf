resource "aws_backup_vault" "vault" {
  name        = "${var.source_account_name}-backup-vault"
  kms_key_arn = aws_kms_key.destination_backup_key.arn
}

output "vault_arn" {
  value = aws_backup_vault.vault.arn
}

output "destination_vault_id" {
  # The ARN of the backup vault in the destination account is needed by
  # the source account to copy backups into it.
  value = local.destination_account_id
}
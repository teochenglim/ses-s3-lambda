resource "null_resource" "workmail_setup" {
  provisioner "local-exec" {
    command = <<EOT
      # Check/create organization
      ORG_ID=$(aws workmail list-organizations --region ${var.aws_region} \
        --query "OrganizationSummaries[?Alias=='${var.organization_alias}'].OrganizationId" \
        --output text)
      
      if [ -z "$ORG_ID" ]; then
        ORG_ID=$(aws workmail create-organization \
          --alias "${var.organization_alias}" \
          --region ${var.aws_region} \
          --query 'OrganizationId' \
          --output text)
        echo "Created WorkMail organization: $ORG_ID"
      else
        echo "Organization already exists: $ORG_ID"
      fi

      # Check/create user
      USER_EXISTS=$(aws workmail list-users --organization-id $ORG_ID \
        --region ${var.aws_region} \
        --query "length(Users[?Name=='${var.workmail_user_name}'])")
      
      if [ "$USER_EXISTS" = "0" ]; then
        aws workmail create-user \
          --organization-id $ORG_ID \
          --name "${var.workmail_user_name}" \
          --display-name "Test User" \
          --password '${var.workmail_user_password}' \
          --region ${var.aws_region}
        echo "Created WorkMail user: ${var.workmail_user_name}"
      else
        echo "User already exists"
      fi

      # Check if user is disabled
      USER_STATE=$(aws workmail list-users \
        --organization-id $ORG_ID \
        --region ${var.aws_region} \
        --query "Users[?Name=='${var.workmail_user_name}'].State" \
        --output text)

      if [ "$USER_STATE" = "DISABLED" ]; then
        aws workmail enable-user \
          --organization-id $ORG_ID \
          --user-id $USER_ID \
          --email "${var.workmail_user_name}@${var.organization_alias}" \
          --region ${var.aws_region}
        echo "Enabled WorkMail user: ${var.workmail_user_name}"
      else
        echo "User is already enabled or not in a disabled state"
      fi
    EOT
  }

  triggers = {
    always_run = timestamp() # Ensure it runs every time
  }
}

# Direct SES activation through Terraform (no need for null resource)
resource "aws_ses_active_receipt_rule_set" "main" {
  rule_set_name = aws_ses_receipt_rule_set.main.rule_set_name
  depends_on    = [null_resource.workmail_setup]
}
resource "null_resource" "workmail_setup" {
  provisioner "local-exec" {
    command = <<EOT
      set -e

      echo "🔍 Checking for existing WorkMail organization with alias '${var.organization_alias}'..."
      ORG_INFO=$(aws workmail list-organizations --region ${var.aws_region} \
        --query "OrganizationSummaries[?Alias=='${var.organization_alias}']" \
        --output json)

      ORG_ID=$(echo "$ORG_INFO" | jq -r '.[0].OrganizationId')
      ORG_STATE=$(echo "$ORG_INFO" | jq -r '.[0].State')

      if [ "$ORG_STATE" = "DELETED" ]; then
        echo "❌ Organization '${var.organization_alias}' is in DELETED state. Exiting..."
        exit 1
      fi

      if [ -z "$ORG_ID" ] || [ "$ORG_ID" = "null" ]; then
        echo "🚀 Creating WorkMail organization..."
        ORG_ID=$(aws workmail create-organization \
          --alias "${var.organization_alias}" \
          --region ${var.aws_region} \
          --query 'OrganizationId' \
          --output text)
        echo "✅ Created WorkMail organization: $ORG_ID"
      else
        echo "ℹ️  Organization already exists: $ORG_ID"
      fi

      echo "🔍 Checking if user '${var.workmail_user_name}' exists..."
      USER_EXISTS=$(aws workmail list-users --organization-id $ORG_ID \
        --region ${var.aws_region} \
        --query "length(Users[?Name=='${var.workmail_user_name}'])")

      if [ "$USER_EXISTS" = "0" ]; then
        echo "👤 Creating WorkMail user '${var.workmail_user_name}'..."
        aws workmail create-user \
          --organization-id $ORG_ID \
          --name "${var.workmail_user_name}" \
          --display-name "Test User" \
          --password '${var.workmail_user_password}' \
          --region ${var.aws_region}
        echo "✅ Created WorkMail user"
      else
        echo "ℹ️  User already exists"
      fi

      echo "🔍 Checking user state and enabling mailbox if necessary..."
      USER_ID=$(aws workmail list-users --organization-id $ORG_ID \
        --region ${var.aws_region} \
        --query "Users[?Name=='${var.workmail_user_name}'].Id" \
        --output text)

      USER_STATE=$(aws workmail list-users --organization-id $ORG_ID \
        --region ${var.aws_region} \
        --query "Users[?Name=='${var.workmail_user_name}'].State" \
        --output text)

      if [ "$USER_STATE" = "DISABLED" ]; then
        echo "🔓 Enabling WorkMail for user '${var.workmail_user_name}'..."
        aws workmail register-to-work-mail \
          --organization-id "$ORG_ID" \
          --entity-id "$USER_ID" \
          --email "${var.workmail_user_name}@${var.organization_alias}.awsapps.com" \
          --region ${var.aws_region}
        echo "✅ Enabled mailbox for user"
      else
        echo "ℹ️  User already enabled or in state: $USER_STATE"
      fi
    EOT
  }

  triggers = {
    always_run = timestamp()
  }
}

# Direct SES activation through Terraform (no need for null resource)
resource "aws_ses_active_receipt_rule_set" "main" {
  rule_set_name = aws_ses_receipt_rule_set.main.rule_set_name
  depends_on    = [null_resource.workmail_setup]
}
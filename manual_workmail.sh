#!/bin/bash

# === CONFIGURATION ===
AWS_REGION="us-west-2"
ORG_ALIAS="chenglimteo5"
USER_NAME="test"
USER_PASSWORD="YourStrongPassword123!"  # Must meet WorkMail password policy

# === FUNCTIONS ===

# Step 1: Check or create WorkMail organization
echo "🔍 Checking for existing WorkMail organization with alias '$ORG_ALIAS'..."
ORG_ID=$(aws workmail list-organizations \
  --region "$AWS_REGION" \
  --query "OrganizationSummaries[?Alias=='$ORG_ALIAS'].OrganizationId" \
  --output text)

if [ -z "$ORG_ID" ]; then
  echo "🚀 Creating WorkMail organization..."
  ORG_ID=$(aws workmail create-organization \
    --alias "$ORG_ALIAS" \
    --region "$AWS_REGION" \
    --query "OrganizationId" \
    --output text)
  echo "✅ Created WorkMail organization: $ORG_ID"
else
  echo "ℹ️  Organization already exists: $ORG_ID"
fi

# Step 2: Check or create user
echo "🔍 Checking if user '$USER_NAME' exists..."
USER_EXISTS=$(aws workmail list-users \
  --organization-id "$ORG_ID" \
  --region "$AWS_REGION" \
  --query "length(Users[?Name=='$USER_NAME'])")

if [ "$USER_EXISTS" = "0" ]; then
  echo "👤 Creating WorkMail user '$USER_NAME'..."
  USER_ID=$(aws workmail create-user \
    --organization-id "$ORG_ID" \
    --name "$USER_NAME" \
    --display-name "Test User" \
    --password "$USER_PASSWORD" \
    --region "$AWS_REGION" \
    --query "UserId" \
    --output text)
  echo "✅ Created WorkMail user: $USER_NAME (ID: $USER_ID)"
else
  echo "ℹ️  User already exists"
  USER_ID=$(aws workmail list-users \
    --organization-id "$ORG_ID" \
    --region "$AWS_REGION" \
    --query "Users[?Name=='$USER_NAME'].Id" \
    --output text)
fi

# Step 3: Enable user if disabled
USER_STATE=$(aws workmail list-users \
  --organization-id "$ORG_ID" \
  --region "$AWS_REGION" \
  --query "Users[?Name=='$USER_NAME'].State" \
  --output text)

if [ "$USER_STATE" = "DISABLED" ]; then
  echo "🔓 Enabling user '$USER_NAME'..."
  aws workmail enable-user \
    --organization-id "$ORG_ID" \
    --user-id "$USER_ID" \
    --email "${USER_NAME}@${ORG_ALIAS}" \
    --region "$AWS_REGION"
  echo "✅ Enabled WorkMail user: $USER_NAME"
else
  echo "ℹ️  User is already enabled or in state: $USER_STATE"
fi

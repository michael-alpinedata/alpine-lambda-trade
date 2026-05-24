data "aws_caller_identity" "current" {}

resource "aws_iam_role" "snowflake_s3_role" {
  name = "alt-snowflake-s3-role"
  
  # Bootstrap Trust Policy: 
  # Autorise temporairement le compte AWS courant pour permettre à Terraform de créer le rôle.
  # Une fois `terraform apply` terminé, tu dois mettre à jour cette "Trust Relationship" dans AWS
  # en utilisant les Outputs `snowflake_storage_aws_iam_user_arn` et `snowflake_storage_aws_external_id`.
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = snowflake_storage_integration.alt_s3_integration.storage_aws_iam_user_arn
        }
        Condition = {
          StringEquals = {
            "sts:ExternalId" = snowflake_storage_integration.alt_s3_integration.storage_aws_external_id
          }
        }
      }
    ]
  })
}

resource "aws_iam_policy" "snowflake_s3_policy" {
  name        = "alt-snowflake-s3-policy"
  description = "Permissions for Snowflake to access alt-raw-data S3 bucket"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::alt-raw-data-${data.aws_caller_identity.current.account_id}",
          "arn:aws:s3:::alt-raw-data-${data.aws_caller_identity.current.account_id}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "snowflake_s3_attach" {
  role       = aws_iam_role.snowflake_s3_role.name
  policy_arn = aws_iam_policy.snowflake_s3_policy.arn
}

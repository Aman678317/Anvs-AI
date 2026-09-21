# ==============================================================================
# Terraform Cloud Infrastructure Outputs (PR-20)
# ==============================================================================

output "vpc_id" {
  description = "Identifier of the primary VPC"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs for Kubernetes nodes and workloads"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs for Internet-facing load balancers"
  value       = aws_subnet.public[*].id
}

output "database_endpoint" {
  description = "Connection endpoint address for Managed PostgreSQL"
  value       = aws_db_instance.postgres.endpoint
}

output "database_name" {
  description = "Primary PostgreSQL database name"
  value       = aws_db_instance.postgres.db_name
}

output "redis_primary_endpoint" {
  description = "Primary connection endpoint for Redis Streams replication group"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "recordings_s3_bucket" {
  description = "Name of the S3 storage bucket for encrypted meeting recordings"
  value       = aws_s3_bucket.recordings.id
}

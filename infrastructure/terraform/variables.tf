# ==============================================================================
# Terraform Cloud Infrastructure Variables (PR-20)
# ==============================================================================

variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "Target AWS deployment region"
}

variable "environment" {
  type        = string
  default     = "production"
  description = "Target deployment environment tier (staging, production)"
}

variable "cluster_name" {
  type        = string
  default     = "meeting-platform-prod"
  description = "EKS Kubernetes cluster name"
}

variable "vpc_cidr" {
  type        = string
  default     = "10.0.0.0/16"
  description = "VPC CIDR block"
}

variable "availability_zones" {
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
  description = "Availability zones for multi-AZ high availability"
}

variable "db_instance_class" {
  type        = string
  default     = "db.r6g.xlarge"
  description = "RDS PostgreSQL instance class for pgvector embeddings"
}

variable "db_allocated_storage" {
  type        = number
  default     = 100
  description = "Initial allocated storage in GB for PostgreSQL"
}

variable "redis_node_type" {
  type        = string
  default     = "cache.r6g.large"
  description = "ElastiCache Redis node type for high-throughput stream bus"
}

variable "redis_num_cache_nodes" {
  type        = number
  default     = 3
  description = "Number of cluster cache nodes for multi-AZ failover"
}

variable "domain_name" {
  type        = string
  default     = "meeting.enterprise.ai"
  description = "Apex domain name for TLS certificate and ingress"
}

terraform {
  required_version = ">= 1.5"
  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.12"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.27"
    }
  }
}

variable "namespace" {
  type        = string
  description = "Kubernetes namespace to deploy LoadDensity into."
  default     = "loaddensity"
}

variable "image_repository" {
  type        = string
  description = "Container image repository for LoadDensity."
  default     = "ghcr.io/integration-automation/loaddensity"
}

variable "image_tag" {
  type        = string
  description = "Container image tag."
  default     = "latest"
}

variable "worker_replicas" {
  type        = number
  description = "How many worker pods to run."
  default     = 2
}

variable "action_json" {
  type        = string
  description = "LoadDensity action JSON to mount into pods."
  default     = "{\"load_density\": []}"
}

resource "kubernetes_namespace" "loaddensity" {
  metadata {
    name = var.namespace
  }
}

resource "helm_release" "loaddensity" {
  name       = "loaddensity"
  namespace  = kubernetes_namespace.loaddensity.metadata[0].name
  chart      = "${path.module}/../helm/loaddensity"

  set {
    name  = "image.repository"
    value = var.image_repository
  }
  set {
    name  = "image.tag"
    value = var.image_tag
  }
  set {
    name  = "workers.replicas"
    value = var.worker_replicas
  }
  set {
    name  = "actionConfigMap.data"
    value = var.action_json
  }
}

output "master_service" {
  description = "ClusterIP service exposing the master."
  value       = "loaddensity-master.${var.namespace}.svc.cluster.local"
}

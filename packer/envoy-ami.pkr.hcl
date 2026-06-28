# Hashicorp Packer build file — historical reference only.
# Historical reference: how Envoy AMIs were built pre-Kubernetes (circa 2015-2018).
# In the modern version, Kubernetes + Docker replaces this entire flow.
#
# Original flow:
#   packer build → launches temp EC2 → uploads SaltStack states →
#   runs salt-call → snapshots disk → creates AMI → terminates EC2
#
# The AMI is then referenced by the CloudFormation AutoScaling Group.

packer {
  required_plugins {
    amazon = {
      version = ">= 1.3.0"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

variable "aws_region" {
  default = "us-east-1"
}

variable "instance_type" {
  default = "t3.medium"
}

variable "base_ami" {
  description = "Ubuntu 22.04 LTS base AMI ID"
  default     = "ami-0c7217cdde317cfec"
}

source "amazon-ebs" "envoy-proxy" {
  region        = var.aws_region
  instance_type = var.instance_type
  source_ami    = var.base_ami
  ssh_username  = "ubuntu"

  ami_name        = "atlassian-envoy-proxy-{{timestamp}}"
  ami_description = "Envoy proxy fleet AMI — pre-baked with Envoy, sidecars, observability"

  tags = {
    Project   = "load-balancer"
    ManagedBy = "packer"
    Component = "envoy-proxy"
  }
}

build {
  sources = ["source.amazon-ebs.envoy-proxy"]

  # Upload SaltStack states
  provisioner "file" {
    source      = "salt/"
    destination = "/tmp/salt/"
  }

  # Bootstrap Salt and run all states
  provisioner "shell" {
    inline = [
      "sudo apt-get update -qq",
      "sudo apt-get install -y -qq salt-minion",
      "sudo mkdir -p /srv/salt",
      "sudo cp -r /tmp/salt/* /srv/salt/",
      "sudo salt-call --local state.apply envoy",
      "sudo salt-call --local state.apply logging",
      "sudo salt-call --local state.apply security",
      "sudo salt-call --local state.apply network-tuning",
      "sudo salt-call --local state.apply containers",
      "sudo salt-call --local state.apply observability",
    ]
  }

  # Verify Envoy is installed correctly
  provisioner "shell" {
    inline = [
      "envoy --version",
      "systemctl is-enabled envoy",
    ]
  }
}

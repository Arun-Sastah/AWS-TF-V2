import os
import subprocess
import logging
import textwrap
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def generate_root_terraform_files(device_id: str, instance_name: str, path: str):
    """
    Generate Terraform root files for a device using AWS default VPC/subnet/security group.
    """
    logger.info(f"Generating Terraform files for device: {device_id} at {path}")
    os.makedirs(path, exist_ok=True)

    # Minimal main.tf using only defaults
    main_tf = textwrap.dedent(f"""
    module "ec2" {{
      source        = "../../modules/ec2"
      ami           = "ami-0c02fb55956c7d316"
      instance_type = "t3.micro"
      instance_name = "{instance_name}"
      device_id     = "{device_id}"
    }}
    """)

    variables_tf = textwrap.dedent("""
    variable "device_id" {
      description = "Unique device identifier"
      type        = string
    }

    variable "instance_name" {
      description = "Name tag for EC2 instance"
      type        = string
    }
    """)

    outputs_tf = textwrap.dedent("""
    output "ec2_instance_id" {
      description = "ID of the EC2 instance"
      value       = module.ec2.instance_id
    }

    output "ec2_public_ip" {
      description = "Public IP of the EC2 instance"
      value       = module.ec2.public_ip
    }
    """)

    provider_tf = textwrap.dedent(f"""
    terraform {{
      required_version = ">= 1.1.0"

      backend "s3" {{
        bucket         = "infra-state-blitz-2025"
        key            = "state/{device_id}.tfstate"
        region         = "us-east-1"
        dynamodb_table = "terraform-locks"
        encrypt        = true
      }}
    }}

    provider "aws" {{
      region = "us-east-1"
    }}
    """)

    files = {
        "main.tf": main_tf,
        "variables.tf": variables_tf,
        "outputs.tf": outputs_tf,
        "provider.tf": provider_tf,
    }

    for filename, content in files.items():
        file_path = os.path.join(path, filename)
        with open(file_path, "w") as f:
            f.write(content.strip() + "\n")

    logger.info(f"Terraform files written successfully at {path}")


def run_terraform_commands(path: str, device_id: str, instance_name: str):
    """
    Run terraform init & apply, return success flag, combined output, and duration.
    """
    start_time = datetime.utcnow()
    output_logs = ""

    logger.info(f"Running 'terraform init' in {path}...")
    try:
        init_result = subprocess.run(
            ["terraform", "init", "-input=false"],
            cwd=path,
            check=True,
            capture_output=True,
            text=True
        )
        output_logs += init_result.stdout + "\n" + init_result.stderr
    except subprocess.CalledProcessError as e:
        output_logs += e.stdout + "\n" + e.stderr
        logger.error(f"Terraform init failed: {e}")
        return False, output_logs, 0

    logger.info(f"Running 'terraform apply' in {path}...")
    try:
        apply_result = subprocess.run(
            [
                "terraform", "apply",
                "-auto-approve",
                "-input=false",
                f"-var=device_id={device_id}",
                f"-var=instance_name={instance_name}"
            ],
            cwd=path,
            check=True,
            capture_output=True,
            text=True
        )
        output_logs += apply_result.stdout + "\n" + apply_result.stderr
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info("Terraform apply completed successfully.")
        return True, output_logs, duration
    except subprocess.CalledProcessError as e:
        output_logs += e.stdout + "\n" + e.stderr
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.error(f"Terraform apply failed: {e}")
        return False, output_logs, duration


def destroy_terraform_resources(path: str, device_id: str, instance_name: str):
    """
    Run terraform destroy, return success flag, output, and duration.
    """
    start_time = datetime.utcnow()
    output_logs = ""

    logger.info(f"Running 'terraform destroy' in {path}...")
    try:
        destroy_result = subprocess.run(
            [
                "terraform",
                "destroy",
                "-auto-approve",
                "-input=false",
                "-var", f"device_id={device_id}",
                "-var", f"instance_name={instance_name}"
            ],
            cwd=path,
            check=True,
            capture_output=True,
            text=True
        )
        output_logs += destroy_result.stdout + "\n" + destroy_result.stderr
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info("Terraform destroy completed successfully.")
        return True, output_logs, duration
    except subprocess.CalledProcessError as e:
        output_logs += e.stdout + "\n" + e.stderr
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.error(f"Terraform destroy failed: {e}")
        return False, output_logs, duration

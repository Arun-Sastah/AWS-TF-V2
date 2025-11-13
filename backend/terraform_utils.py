import os
import asyncio
import logging
import textwrap
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# -------------------------
# Terraform File Generation
# -------------------------
def generate_root_terraform_files(device_id: str, instance_name: str, path: str):
    os.makedirs(path, exist_ok=True)
    logger.info(f"Generating Terraform files for device: {device_id} at {path}")

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
      description = "EC2 instance name"
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
        with open(os.path.join(path, filename), "w") as f:
            f.write(content.strip() + "\n")

    logger.info(f"Terraform files written successfully at {path}")

# -------------------------
# Async Terraform Execution
# -------------------------
async def run_terraform_commands(path: str, device_id: str, instance_name: str):
    start_time = datetime.utcnow()
    output_logs = ""

    async def run_cmd(cmd):
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode, stdout.decode(), stderr.decode()

    # terraform init
    ret, out, err = await run_cmd(["terraform", "init", "-input=false"])
    output_logs += out + "\n" + err
    if ret != 0:
        logger.error("Terraform init failed")
        return False, output_logs, 0

    # terraform apply
    ret, out, err = await run_cmd([
        "terraform", "apply", "-auto-approve", "-input=false",
        f"-var=device_id={device_id}", f"-var=instance_name={instance_name}"
    ])
    output_logs += out + "\n" + err
    duration = (datetime.utcnow() - start_time).total_seconds()
    success = ret == 0
    return success, output_logs, duration

async def destroy_terraform_resources(path: str, device_id: str, instance_name: str):
    start_time = datetime.utcnow()
    output_logs = ""

    async def run_cmd(cmd):
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode, stdout.decode(), stderr.decode()

    ret, out, err = await run_cmd([
        "terraform", "destroy", "-auto-approve", "-input=false",
        f"-var=device_id={device_id}", f"-var=instance_name={instance_name}"
    ])
    output_logs += out + "\n" + err
    duration = (datetime.utcnow() - start_time).total_seconds()
    success = ret == 0
    return success, output_logs, duration

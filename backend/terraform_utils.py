import os
import random
import string

TEMPLATE_DIR = "/app/terraform_templates"

def random_suffix(length=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def generate_terraform_files(device_id, instance_count=1, path=None):
    """
    Generate Terraform files with AWS EC2 instance(s) and S3 backend.
    Each device gets its own folder.
    """
    tf_dir = path or os.path.join(TEMPLATE_DIR, device_id)
    os.makedirs(tf_dir, exist_ok=True)

    # main.tf content
    main_tf = f"""
provider "aws" {{
  region = "us-east-1"
}}

resource "aws_instance" "example" {{
  ami           = "ami-0c02fb55956c7d316"
  instance_type = "t3.micro"
  count         = {instance_count}

  tags = {{
    Name = "{device_id}-instance-${{count.index + 1}}"
  }}
}}
"""
    with open(os.path.join(tf_dir, "main.tf"), "w") as f:
        f.write(main_tf)

    # backend.tf content
    backend_tf = f"""
terraform {{
  backend "s3" {{
    bucket = "infra-state-blitz-2025"
    key    = "{device_id}/terraform.tfstate"
    region = "us-east-1"
  }}
}}
"""
    with open(os.path.join(tf_dir, "backend.tf"), "w") as f:
        f.write(backend_tf)

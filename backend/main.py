from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import subprocess, boto3, json
from datetime import datetime
import os
from terraform_utils import generate_terraform_files, random_suffix

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# AWS DynamoDB client
dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
audit_table_name = os.getenv("DYNAMO_TABLE", "terraform-locks")
audit_table = dynamodb.Table(audit_table_name)

# Local audit file
LOCAL_AUDIT_FILE = "audit_log.json"

def log_audit(device_id, user, action, resource_id, status):
    """
    Logs every action to both DynamoDB and local JSON file.
    """
    item = {
        "LockID": device_id,
        "timestamp": datetime.utcnow().isoformat(),
        "user": user,
        "action": action,
        "resource_id": resource_id or "",
        "status": status
    }

    # Log to DynamoDB
    try:
        audit_table.put_item(Item=item)
    except Exception as e:
        print(f"[WARN] DynamoDB logging failed: {e}")

    # Log to local file
    try:
        with open(LOCAL_AUDIT_FILE, "a") as f:
            f.write(json.dumps(item) + "\n")
    except Exception as e:
        print(f"[WARN] Local logging failed: {e}")

@app.post("/create-server")
async def create_server(request: Request):
    body = await request.json()
    user = body.get("user", "anonymous")
    device_id = body.get("device_id", random_suffix())

    # Device-specific Terraform directory
    tf_dir = f"/app/terraform_templates/{device_id}"
    os.makedirs(tf_dir, exist_ok=True)
    generate_terraform_files(device_id, path=tf_dir)

    # Terraform init with backend config
    proc_init = subprocess.run(
        [
            "terraform", "init",
            "-backend-config", "bucket=infra-state-blitz-2025",
            "-backend-config", f"key={device_id}/terraform.tfstate",
            "-backend-config", "region=us-east-1"
        ],
        cwd=tf_dir, capture_output=True, text=True
    )

    if proc_init.returncode != 0:
        log_audit(device_id, user, "terraform_init", None, "failed")
        raise HTTPException(status_code=500, detail=proc_init.stderr)
    
    log_audit(device_id, user, "terraform_init", None, "success")

    # Terraform apply
    proc_apply = subprocess.run(
        ["terraform", "apply", "-auto-approve"],
        cwd=tf_dir, capture_output=True, text=True
    )
    if proc_apply.returncode != 0:
        log_audit(device_id, user, "create_server", None, "failed")
        raise HTTPException(status_code=500, detail=proc_apply.stderr)

    # Capture Terraform output
    resource_id = None
    try:
        terraform_output = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=tf_dir, capture_output=True, text=True
        )
        outputs = json.loads(terraform_output.stdout)
        resource_id = outputs.get("aws_instance_example_id", {}).get("value")
    except Exception as e:
        print(f"[ERROR] Failed to parse Terraform output: {e}")

    log_audit(device_id, user, "create_server", resource_id, "success")
    return {"message": "Server created", "device_id": device_id, "resource_id": resource_id}

@app.post("/destroy-server")
async def destroy_server(request: Request):
    body = await request.json()
    device_id = body["device_id"]
    user = body.get("user", "anonymous")
    tf_dir = f"/app/terraform_templates/{device_id}"

    proc_destroy = subprocess.run(
        ["terraform", "destroy", "-auto-approve"],
        cwd=tf_dir, capture_output=True, text=True
    )
    status = "success" if proc_destroy.returncode == 0 else "failed"
    log_audit(device_id, user, "destroy_server", None, status)

    if proc_destroy.returncode != 0:
        raise HTTPException(status_code=500, detail=proc_destroy.stderr)

    return {"message": "Destroyed", "device_id": device_id}

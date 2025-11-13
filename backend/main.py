from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import os
import logging
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from terraform_utils import generate_root_terraform_files, run_terraform_commands, destroy_terraform_resources
from db import log_action  # <-- our async PostgreSQL logging function

# -------------------------
# Logging setup
# -------------------------
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# -------------------------
# FastAPI app setup
# -------------------------
app = FastAPI(title="Terraform Deployment API", version="1.0.0")

origins = ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Request model
# -------------------------
class DeployRequest(BaseModel):
    user: str = Field(..., description="User triggering deployment")
    device_id: str = Field(..., min_length=3, max_length=50, description="Device ID")
    instance_name: str = Field(..., min_length=3, max_length=100, description="EC2 instance name")

# -------------------------
# Create server endpoint
# -------------------------
@app.post("/create-server")
async def create_server(request: DeployRequest):
    device_path = os.path.join("terraform_templates", request.device_id)
    await log_action(request.device_id, "started", status="started")  # log start

    try:
        # Generate Terraform files
        generate_root_terraform_files(request.device_id, request.instance_name, device_path)

        # Run Terraform commands
        success, output, duration = await run_terraform_commands(
            path=device_path,
            device_id=request.device_id,
            instance_name=request.instance_name
        )

        status = "success" if success else "failed"
        await log_action(
            request_id=int(request.device_id),
            status=status,
            terraform_apply=output,
            duration_seconds=duration,
            terraform_apply_log=output
        )

        if not success:
            raise HTTPException(status_code=500, detail="Terraform apply failed")

        return {"message": f"Server created for device {request.device_id}", "device_id": request.device_id}

    except Exception as e:
        await log_action(
            request_id=int(request.device_id),
            status="error",
            terraform_apply_log=str(e)
        )
        logger.error(f"Error creating server: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error")

# -------------------------
# Destroy server endpoint
# -------------------------
@app.post("/destroy-server")
async def destroy_server(request: DeployRequest):
    device_path = os.path.join("terraform_templates", request.device_id)
    await log_action(request.device_id, "destroy_started", status="started")  # log start

    try:
        # Run Terraform destroy
        success, output, duration = await destroy_terraform_resources(
            path=device_path,
            device_id=request.device_id,
            instance_name=request.instance_name
        )

        status = "success" if success else "failed"
        await log_action(
            request_id=int(request.device_id),
            status=status,
            terraform_apply=output,
            duration_seconds=duration,
            terraform_apply_log=output
        )

        if not success:
            raise HTTPException(status_code=500, detail="Terraform destroy failed")

        return {"message": f"Server destroyed for device {request.device_id}"}

    except Exception as e:
        await log_action(
            request_id=int(request.device_id),
            status="error",
            terraform_apply_log=str(e)
        )
        logger.error(f"Error destroying server: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error")

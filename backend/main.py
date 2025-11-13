from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import os
import logging
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from terraform_utils import (
    generate_root_terraform_files,
    run_terraform_commands,
    destroy_terraform_resources,
)
from db_utils import log_request, log_resource  # Async PostgreSQL logging

# -------------------------
# Logging setup
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
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
# Helper functions for logging
# -------------------------
async def log_start(request_id: int, user: str, action: str):
    """Create a new log entry at the start of a request."""
    log_id = await log_request(
        request_id=request_id,
        user_id=user,
        status=action,
        created_at=datetime.utcnow()
    )
    return {"log_id": log_id, "request_id": request_id}


async def log_end(request_id: int, user: str, status: str, duration: float = None, error: str = None):
    """Update or finalize a log entry."""
    log_id = await log_request(
        request_id=request_id,
        user_id=user,
        status=status,
        duration_seconds=duration,
        created_at=datetime.utcnow(),
        error_message=error
    )
    return {"log_id": log_id, "request_id": request_id}


async def log_resource_creation(log_id: int, resource_type: str, resource_name: str, resource_id_value: str):
    """Log a created resource in request_resources table."""
    return await log_resource(
        log_id=log_id,
        resource_type=resource_type,
        resource_name=resource_name,
        resource_id_value=resource_id_value
    )

# -------------------------
# Create server endpoint
# -------------------------
@app.post("/create-server")
async def create_server(request: DeployRequest):
    device_path = os.path.join("terraform_templates", request.device_id)

    # Log start of operation
    log_entry = await log_start(request_id=int(request.device_id), user=request.user, action="create_started")

    try:
        log_id = log_entry.get("log_id") if isinstance(log_entry, dict) else getattr(log_entry, "log_id", None)

        logger.info(f"Generating Terraform files for device: {request.device_id} at {device_path}")
        generate_root_terraform_files(request.device_id, request.instance_name, device_path)
        logger.info(f"Terraform files written successfully at {device_path}")

        success, output, duration = await run_terraform_commands(
            path=device_path,
            device_id=int(request.device_id),
            instance_name=request.instance_name
        )

        status = "success" if success else "failed"

        await log_end(
            request_id=int(request.device_id),
            user=request.user,
            status=status,
            duration=duration,
            error=None if success else output
        )

        if success:
            await log_resource_creation(
                log_id=log_id,
                resource_type="EC2",
                resource_name=request.instance_name,
                resource_id_value=request.device_id
            )

        if not success:
            raise HTTPException(status_code=500, detail="Terraform apply failed")

        return {"message": f"Server created for device {request.device_id}", "device_id": request.device_id}

    except Exception as e:
        logger.error(f"Error creating server: {e}", exc_info=True)
        await log_end(
            request_id=int(request.device_id),
            user=request.user,
            status="error",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------
# Destroy server endpoint
# -------------------------
@app.post("/destroy-server")
async def destroy_server(request: DeployRequest):
    device_path = os.path.join("terraform_templates", request.device_id)

    # Log start of destroy
    log_entry = await log_start(request_id=int(request.device_id), user=request.user, action="destroy_started")

    try:
        log_id = log_entry.get("log_id") if isinstance(log_entry, dict) else getattr(log_entry, "log_id", None)

        success, output, duration = await destroy_terraform_resources(
            path=device_path,
            device_id=int(request.device_id),
            instance_name=request.instance_name
        )

        status = "success" if success else "failed"

        await log_end(
            request_id=int(request.device_id),
            user=request.user,
            status=status,
            duration=duration,
            error=None if success else output
        )

        if success:
            await log_resource_creation(
                log_id=log_id,
                resource_type="EC2",
                resource_name=request.instance_name,
                resource_id_value=f"DESTROYED-{request.device_id}"
            )

        if not success:
            raise HTTPException(status_code=500, detail="Terraform destroy failed")

        return {"message": f"Server destroyed for device {request.device_id}"}

    except Exception as e:
        logger.error(f"Error destroying server: {e}", exc_info=True)
        await log_end(
            request_id=int(request.device_id),
            user=request.user,
            status="error",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

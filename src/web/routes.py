"""
All of the routes for the FastAPI application will be defined here.
"""

import json
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from jobs import job_manager, serialize_job_data
from pydantic import ValidationError
from starlette.status import HTTP_302_FOUND, HTTP_303_SEE_OTHER

from web.auth import authenticate_user, get_current_user, oauth
from web.models import JobSubmission, User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def read_root(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)
    return FileResponse("src/web/html/index.html")


@router.get("/login")
async def login(request: Request):
    nonce = secrets.token_urlsafe()
    request.session["oauth_nonce"] = nonce
    redirect_uri = request.url_for("oauth_redirect")
    return await oauth.google.authorize_redirect(request, redirect_uri, nonce=nonce)


@router.get("/oauth-redirect")
async def oauth_redirect(request: Request):
    try:
        user_info = await authenticate_user(request)
        request.session["user"] = user_info
        return RedirectResponse(url="/")
    except HTTPException as e:
        return RedirectResponse(url=f"/auth-error?error={e.detail}")


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)


@router.get("/protected")
async def protected_route(user: User = Depends(get_current_user)):
    return {"message": f"Hello, {user.email}! This is a protected route."}


@router.post("/submission")
async def submission(job_data: JobSubmission, user: User = Depends(get_current_user)):
    logger.info(f"Received job submission: {job_data.dict()}")
    try:
        # Convert locations back to a list if it's a JSON string
        if isinstance(job_data.locations, str):
            job_data.locations = json.loads(job_data.locations)

        # Ensure seedKeywords is a list
        if isinstance(job_data.seedKeywords, str):
            job_data.seedKeywords = [
                kw.strip() for kw in job_data.seedKeywords.split(",")
            ]

        # Create a dictionary with the current page data
        current_page = {
            "url": job_data.pageUrl,
            "title": job_data.pageTitle,
            "info": job_data.pageInfo,
            "usp": job_data.pageUsp,
            "is_new": job_data.isNewPage,
        }

        # Prepare the job data
        job_dict = job_data.dict()
        job_dict["current_page"] = current_page

        # Remove the individual page fields from the top level
        for field in ["pageUrl", "pageTitle", "pageInfo", "pageUsp", "isNewPage"]:
            job_dict.pop(field, None)

        # Serialize the job data
        serialized_job_dict = serialize_job_data(job_dict)

        logger.info(f"Submitting job with data: {serialized_job_dict}")
        job_id = await job_manager.create_job(serialized_job_dict)
        return {"job_id": job_id}
    except ValidationError as ve:
        logger.error(f"Validation error: {ve.json()}")
        raise HTTPException(status_code=422, detail=ve.errors())
    except Exception as e:
        logger.exception(f"Error creating job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")


@router.get("/heartbeat/{job_id}")
async def heartbeat(job_id: str, user: User = Depends(get_current_user)):
    job_status = await job_manager.get_detailed_job_status(job_id)
    if job_status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    logger.debug(f"Heartbeat for job {job_id}: {job_status}")
    return job_status


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


@router.get("/auth-error")
async def auth_error(request: Request):
    error = request.query_params.get("error", "unknown_error")
    return {"error": error, "message": "Authentication failed"}


@router.get("/job/{job_id}")
async def get_job_details(job_id: str, user: User = Depends(get_current_user)):
    job_details = await job_manager.get_job_with_tasks_and_versions(job_id)
    if job_details is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_details

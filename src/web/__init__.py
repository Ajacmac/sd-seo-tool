import os

from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Mount a static files directory
app.mount("/static", StaticFiles(directory="src/web"), name="static")

SECRET_KEY = os.getenv("OAUTH_SESSION_KEY")

# Hardcoded list of authorized email addresses
AUTHORIZED_DOMAIN = "samson.digital"
AUTHORIZED_EMAILS = ["projects@samson.digital", "info@samson.digital"]

# Set up OAuth
oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://accounts.google.com/o/oauth2/auth",
    tokenUrl="https://oauth2.googleapis.com/token",
)


# add a submission endpoint that accepts a data submission from the seo-tool frontend
# and returns a response with the submission id (the uuid for the db row)


# add a /heartbeat route for the frontend to poll the backend for
# data with a submission id number


job_progress = {}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from vivintpy import Account, VivintSkyApiMfaRequiredError # VivintSkyApiAuthenticationError
from vivintpy_api.config import settings
from vivintpy.event_capture import DoorbellCaptureManager
from vivintpy_api.routers import auth, systems, devices, events # Import other routers as they are ready

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Or use settings.LOG_LEVEL

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize shared Vivint Account and PubNub client
    logger.info("FastAPI app startup: Initializing resources...")
    app.state.vivint_account = None  # Initialize with None
    app.state.doorbell_capture = None

    if settings.VIVINT_USERNAME and settings.VIVINT_PASSWORD:
        logger.info(f"Attempting to initialize shared Vivint Account for user: {settings.VIVINT_USERNAME}")
        shared_account = Account(
            username=settings.VIVINT_USERNAME,
            password=settings.VIVINT_PASSWORD,
            # persist_session_token=True, # Consider if session token should be persisted for shared account
            # refresh_token_file=settings.REFRESH_TOKEN_FILE_PATH # If using refresh token for shared account
        )
        try:
            await shared_account.connect() # This might require MFA if not handled via refresh token
            # TODO: Handle MFA for the shared service account during startup if necessary.
            # This could involve a manual step or a pre-configured refresh token.
            # For now, we assume direct connect or refresh token handles it.
            logger.info("Shared Vivint Account connected successfully.")
            
            # Start PubNub event listener
            # Assuming Account.connect() also establishes PubNub or it's a separate call
            if shared_account.is_connected and hasattr(shared_account, 'connect_stream') and callable(getattr(shared_account, 'connect_stream')):
                await shared_account.connect_stream() # Or similar method to start PubNub
                logger.info("PubNub event stream connected for shared account.")
            
            app.state.vivint_account = shared_account
            # Start doorbell media capture
            capture_mgr = DoorbellCaptureManager(shared_account, settings.MEDIA_ROOT)
            await capture_mgr.start()
            app.state.doorbell_capture = capture_mgr
        except VivintSkyApiMfaRequiredError:
            logger.error(
                "MFA required for the shared Vivint Account configured in settings. "
                "Automatic MFA handling during startup is not implemented. "
                "Please configure a refresh token or handle MFA manually for the service account."
            )
            # Optionally, decide if the app should fail to start or run without a shared account.
            # For now, it will continue without a shared_account if MFA is hit here.
        except Exception as e:
            logger.error(f"Failed to initialize or connect shared Vivint Account: {e}", exc_info=True)
            # Decide on behavior: fail startup or continue without shared account
    else:
        logger.warning("Shared Vivint Account credentials not configured in settings. Skipping shared account initialization.")

    yield

    # Shutdown: Cleanup resources
    logger.info("FastAPI app shutdown: Cleaning up resources...")
    # Stop doorbell capture first
    if app.state.doorbell_capture:
        await app.state.doorbell_capture.stop()

    if app.state.vivint_account:
        shared_account: Account = app.state.vivint_account
        logger.info("Disconnecting shared Vivint Account and PubNub stream...")
        if hasattr(shared_account, 'disconnect_stream') and callable(getattr(shared_account, 'disconnect_stream')):
            await shared_account.disconnect_stream() # Or similar method to stop PubNub
            logger.info("PubNub event stream disconnected for shared account.")
        await shared_account.disconnect()
        logger.info("Shared Vivint Account disconnected.")

api_description = """
The VivintPy API provides a RESTful and WebSocket interface to interact with Vivint smart home systems,
leveraging the `vivintpy` library.

**Features:**
- Secure JWT-based authentication with MFA support.
- Endpoints to manage systems and alarm panels.
- Comprehensive control over various Vivint devices (locks, thermostats, switches, cameras, etc.).
- Real-time event streaming via WebSockets for live updates from your Vivint system.

This API is designed for developers looking to integrate Vivint smart home functionality into their applications.
"""

openapi_tags = [
    {
        "name": "Authentication",
        "description": "Endpoints for user authentication, login, and MFA verification.",
    },
    {
        "name": "Systems",
        "description": "Manage Vivint systems and alarm panels. List systems, get system details, and control panel states (arm, disarm, etc.).",
    },
    {
        "name": "Devices",
        "description": "Interact with Vivint devices. List devices within a system, get device details, and control specific device functionalities (locks, thermostats, switches, cameras, etc.).",
    },
    {
        "name": "Real-time Events",
        "description": "Subscribe to real-time events from the Vivint system via WebSocket.",
    },
]

app = FastAPI(
    title="VivintPy API",
    description=api_description,
    version="0.1.0", # This can be updated as project evolves
    lifespan=lifespan,
    contact={
        "name": "VivintPy API Support",
        "url": "https://github.com/ChrisWondeFro/vivintpy--/issues", # Adjusted placeholder
        "email": "vivintpy.api.dev@example.com", # Placeholder
    },
    license_info={
        "name": "MIT License", # Assuming MIT, adjust if different
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=openapi_tags,
    # openapi_url="/api/v1/openapi.json", # Example custom OpenAPI URL
    # docs_url="/api/docs", # Example custom docs URL
    # redoc_url="/api/redoc" # Example custom ReDoc URL
)

# CORS Middleware
# Adjust allow_origins, allow_methods, etc., as needed for your security requirements.
# For development, ["*"] is often used for allow_origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS if settings.ALLOWED_ORIGINS else ["*"], # Or a specific list of origins
    allow_credentials=True,
    allow_methods=["*"], # Or specify methods like ["GET", "POST"]
    allow_headers=["*"], # Or specify headers
)

# Include routers
app.include_router(auth.router)
app.include_router(systems.router)
app.include_router(devices.router)
app.include_router(events.router)

@app.get("/")
async def root():
    return {"message": "Welcome to VivintPy API. Navigate to /docs for API documentation."}

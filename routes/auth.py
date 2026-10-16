import os
import re
import secrets
from datetime import datetime
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from database import rules

router = APIRouter(tags=["Authentication"])
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates_dir = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=templates_dir)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")


def get_redirect_uri(request: Request | None = None) -> str:
    env_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if env_uri:
        return env_uri
    if request:
        forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
        return f"{forwarded_proto}://{host}/register"
    return "http://localhost:8000/register"

# Regex matching <name>@<dept>.iitr.ac.in as well as @iitr.ac.in
IITR_EMAIL_REGEX = re.compile(r"^[^@]+@([a-zA-Z0-9-]+\.)*iitr\.ac\.in$", re.IGNORECASE)

# Competing Departments Configuration:
# 1. AMSC: Email subdomain 'amsc' -> Department Abbreviation 'AMSC'
# 2. PPE:  Email subdomain 'pe'   -> Department Abbreviation 'PPE'
# 3. PPT:  Email subdomain 'pt'   -> Department Abbreviation 'PPT'

DEPARTMENT_CONFIG: dict[str, dict[str, str]] = {
    "amsc": {
        "code": "amsc",
        "abbr": "AMSC",
        "name": "AMSC",
        "email_domain": "amsc",
    },
    "ppe": {
        "code": "ppe",
        "abbr": "PPE",
        "name": "PPE",
        "email_domain": "pe",
    },
    "ppt": {
        "code": "ppt",
        "abbr": "PPT",
        "name": "PPT",
        "email_domain": "pt",
    },
}

# Subdomain alias mapping (maps email subdomain to canonical dept code)
EMAIL_SUBDOMAIN_TO_DEPT: dict[str, str] = {
    "amsc": "amsc",
    "pe": "ppe",
    "ppe": "ppe",
    "pt": "ppt",
    "ppt": "ppt",
}

# Canonical department codes permitted to compete and access the portal
ALLOWED_DEPARTMENTS: set[str] = {"amsc", "ppe", "ppt"}


def resolve_department(email: str) -> dict[str, str] | None:
    """
    Given an institute email, extracts the subdomain and resolves to the
    canonical department config.
    Returns None if the email is not from one of the 3 competing departments.
    """
    subdomain = extract_department(email)
    if not subdomain:
        return None
    dept_code = EMAIL_SUBDOMAIN_TO_DEPT.get(subdomain.lower())
    if not dept_code or dept_code not in DEPARTMENT_CONFIG:
        return None
    return DEPARTMENT_CONFIG[dept_code]


def is_valid_iitr_email(email: str) -> bool:
    """Check if the email belongs to an IIT Roorkee domain or department subdomain."""
    if not email:
        return False
    return bool(IITR_EMAIL_REGEX.match(email.lower().strip()))


def extract_department(email: str) -> str | None:
    """
    Extract department code from email (e.g., psharma@amsc.iitr.ac.in -> amsc).
    Returns None if no department subdomain exists (e.g., staff@iitr.ac.in).
    """
    if not email or "@" not in email:
        return None
    domain = email.split("@")[-1].lower().strip()
    parts = domain.split(".")
    # Expected student domain: <dept>.iitr.ac.in -> len(parts) >= 4, parts[-3] == 'iitr', parts[-2] == 'ac', parts[-1] == 'in'
    if len(parts) >= 4 and parts[-3] == "iitr" and parts[-2] == "ac" and parts[-1] == "in":
        dept = parts[-4].strip().lower()
        if dept and dept != "iitr":
            return dept
    return None


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render the Google Sign-In portal page."""
    user = request.session.get("user")
    if user:
        return RedirectResponse(url="/register", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "has_google_creds": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        },
    )


@router.get("/auth/google")
async def auth_google(request: Request):
    """Redirect user to Google's OAuth 2.0 consent page."""
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": get_redirect_uri(request),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
        "state": state,
    }

    authorization_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    )
    return RedirectResponse(url=authorization_url)


@router.get("/auth/callback")
async def auth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    """
    Handle Google OAuth 2.0 callback.
    Validates <name>@<dept>.iitr.ac.in format and captures department.
    """
    if error:
        return templates.TemplateResponse(
            request=request,
            name="unauthorized.html",
            context={
                "error_message": f"Google Sign-In was cancelled or failed: {error}",
            },
            status_code=400,
        )

    if not code:
        return RedirectResponse(url="/login", status_code=303)

    saved_state = request.session.pop("oauth_state", None)
    if saved_state and state and saved_state != state:
        return templates.TemplateResponse(
            request=request,
            name="unauthorized.html",
            context={
                "error_message": "Invalid authentication state. Possible CSRF detected.",
            },
            status_code=400,
        )

    # Exchange authorization code for access token with Google
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": get_redirect_uri(request),
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )

        if token_response.status_code != 200:
            return templates.TemplateResponse(
                request=request,
                name="unauthorized.html",
                context={
                    "error_message": "Failed to exchange authorization code with Google.",
                },
                status_code=400,
            )

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        userinfo_response = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if userinfo_response.status_code != 200:
            return templates.TemplateResponse(
                request=request,
                name="unauthorized.html",
                context={
                    "error_message": "Failed to fetch user profile information from Google.",
                },
                status_code=400,
            )

        userinfo = userinfo_response.json()

    # Extract user details
    email = userinfo.get("email", "").lower().strip()
    name = userinfo.get("name") or userinfo.get("given_name", "IITR Athlete")
    picture = userinfo.get("picture", "")

    # Domain verification: accepts any <name>@<dept>.iitr.ac.in or @iitr.ac.in email
    if not is_valid_iitr_email(email):
        request.session.clear()
        return templates.TemplateResponse(
            request=request,
            name="unauthorized.html",
            context={
                "rejected_email": email,
                "error_title": "Invalid Institute Account",
                "error_message": f"Access restricted. You signed in as '{email}', but only accounts ending in *.iitr.ac.in are permitted.",
                "reason": "Please sign in using your official IIT Roorkee Google email.",
            },
            status_code=403,
        )

    # Extract department subdomain & resolve canonical department
    subdomain = extract_department(email)
    dept_info = resolve_department(email) if subdomain else None

    # Rule: Staff or accounts without a department subdomain are not allowed
    if not subdomain:
        request.session.clear()
        return templates.TemplateResponse(
            request=request,
            name="unauthorized.html",
            context={
                "rejected_email": email,
                "detected_dept": "None (Staff / General Account)",
                "error_title": "Staff Accounts Not Permitted",
                "error_message": "Access restricted: Staff and administrative accounts (@iitr.ac.in) without a student department subdomain are not eligible to register or compete.",
                "reason": "Only students from the 3 competing departments (AMSC, PPE, PPT) are permitted to enter.",
            },
            status_code=403,
        )

    # Rule: Only 3 competing departments are allowed
    if not dept_info:
        request.session.clear()
        return templates.TemplateResponse(
            request=request,
            name="unauthorized.html",
            context={
                "rejected_email": email,
                "detected_dept": subdomain.upper(),
                "error_title": "Department Not Competing",
                "error_message": f"Access restricted: Department '{subdomain.upper()}' is not participating in this sports meet.",
                "reason": "This tournament is exclusively between 3 departments: AMSC, PPE, and PPT. Students from other departments are not eligible to participate.",
            },
            status_code=403,
        )

    dept_code = dept_info["code"]
    dept_abbr = dept_info["abbr"]
    dept_email_domain = dept_info["email_domain"]

    user_record = {
        "email": email,
        "name": name,
        "picture": picture,
        "department": dept_code,
        "department_abbr": dept_abbr,
        "department_email_domain": dept_email_domain,
        "role": "athlete",
        "last_login": datetime.utcnow().isoformat(),
    }

    # Save / update user in MongoDB users collection
    try:
        existing_user = await rules.find({"email": email}, collection="users", one=True)
        if not existing_user:
            user_record["created_at"] = datetime.utcnow().isoformat()
            await rules.add(user_record, collection="users")
        else:
            await rules.update({"email": email}, user_record, collection="users")
    except Exception as db_err:
        print(f"Notice: Database write skipped: {db_err}")

    # Store in session
    request.session["user"] = {
        "email": email,
        "name": name,
        "picture": picture,
        "department": dept_code,
        "department_abbr": dept_abbr,
        "department_email_domain": dept_email_domain,
        "role": "athlete",
    }

    return RedirectResponse(url="/register", status_code=303)


@router.get("/dashboard")
async def dashboard_page():
    """Redirect to unified /register page."""
    return RedirectResponse(url="/register", status_code=303)



@router.get("/logout")
async def logout(request: Request):
    """Log out user and clear session."""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

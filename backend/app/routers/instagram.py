from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx

from app.database import get_db
from app.models import User, InstagramConnection
from app.schemas import InstagramConnectionOut, MessageOut
from app.auth import get_current_user, encrypt_token, decrypt_token
from app.config import settings

router = APIRouter(prefix="/api/instagram", tags=["instagram"])

FB_AUTH_URL = "https://www.facebook.com/v18.0/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
IG_SCOPES = "instagram_basic,instagram_content_publish,pages_read_engagement,pages_show_list"


@router.get("/connect")
def connect_instagram(current_user: User = Depends(get_current_user)):
    """Returns the OAuth URL to initiate Instagram connection."""
    if not settings.INSTAGRAM_APP_ID:
        raise HTTPException(status_code=503, detail="Instagram integration not configured")

    # Encode user_id as state for CSRF protection
    import hashlib, hmac
    state = hmac.new(
        settings.SECRET_KEY.encode(),
        current_user.id.encode(),
        hashlib.sha256,
    ).hexdigest() + "." + current_user.id

    url = (
        f"{FB_AUTH_URL}"
        f"?client_id={settings.INSTAGRAM_APP_ID}"
        f"&redirect_uri={settings.INSTAGRAM_REDIRECT_URI}"
        f"&scope={IG_SCOPES}"
        f"&response_type=code"
        f"&state={state}"
    )
    return {"oauth_url": url}


@router.get("/callback")
async def instagram_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle Facebook/Instagram OAuth callback."""
    # Verify state
    import hashlib, hmac as _hmac
    parts = state.split(".")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid state")
    received_sig, user_id = parts[0], parts[1]
    expected = _hmac.new(
        settings.SECRET_KEY.encode(), user_id.encode(), hashlib.sha256
    ).hexdigest()
    if not _hmac.compare_digest(received_sig, expected):
        raise HTTPException(status_code=400, detail="State mismatch")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    async with httpx.AsyncClient() as client:
        # Exchange code for token
        token_resp = await client.post(FB_TOKEN_URL, data={
            "client_id": settings.INSTAGRAM_APP_ID,
            "client_secret": settings.INSTAGRAM_APP_SECRET,
            "redirect_uri": settings.INSTAGRAM_REDIRECT_URI,
            "code": code,
        })
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Token exchange failed")
        token_data = token_resp.json()
        access_token = token_data.get("access_token")

        # Get long-lived token
        ll_resp = await client.get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.INSTAGRAM_APP_ID,
                "client_secret": settings.INSTAGRAM_APP_SECRET,
                "fb_exchange_token": access_token,
            },
        )
        if ll_resp.status_code == 200:
            ll_data = ll_resp.json()
            access_token = ll_data.get("access_token", access_token)
            expires_in = ll_data.get("expires_in", 5184000)  # ~60 days
        else:
            expires_in = 3600

        # Get FB pages to find connected IG account
        pages_resp = await client.get(
            "https://graph.facebook.com/v18.0/me/accounts",
            params={"access_token": access_token, "fields": "id,name,instagram_business_account"},
        )
        ig_account_id = None
        ig_username = None

        if pages_resp.status_code == 200:
            pages = pages_resp.json().get("data", [])
            for page in pages:
                ig_biz = page.get("instagram_business_account", {})
                if ig_biz.get("id"):
                    ig_account_id = ig_biz["id"]
                    # Get username
                    ig_resp = await client.get(
                        f"https://graph.facebook.com/v18.0/{ig_account_id}",
                        params={"fields": "username", "access_token": access_token},
                    )
                    if ig_resp.status_code == 200:
                        ig_username = ig_resp.json().get("username")
                    break

        if not ig_account_id:
            # Redirect to frontend with error
            return RedirectResponse(
                f"{settings.ALLOWED_ORIGINS.split(',')[0]}/connect/instagram?error=no_business_account"
            )

    # Save connection
    existing = db.query(InstagramConnection).filter(
        InstagramConnection.user_id == user.id
    ).first()
    encrypted = encrypt_token(access_token)
    expiry = datetime.utcnow() + timedelta(seconds=expires_in)

    if existing:
        existing.ig_account_id = ig_account_id
        existing.ig_username = ig_username
        existing.access_token_encrypted = encrypted
        existing.token_expiry = expiry
        existing.is_active = True
        existing.last_refresh_at = datetime.utcnow()
    else:
        db.add(InstagramConnection(
            user_id=user.id,
            ig_account_id=ig_account_id,
            ig_username=ig_username,
            access_token_encrypted=encrypted,
            token_expiry=expiry,
            scopes=IG_SCOPES.split(","),
            is_active=True,
        ))
    db.commit()

    return RedirectResponse(
        f"{settings.ALLOWED_ORIGINS.split(',')[0]}/dashboard?ig_connected=1"
    )


@router.get("/status", response_model=dict)
def connection_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conn = db.query(InstagramConnection).filter(
        InstagramConnection.user_id == current_user.id
    ).first()
    if not conn:
        return {"status": "not_connected", "connection": None}
    if not conn.is_active:
        return {"status": "disconnected", "connection": None}
    if conn.token_expiry and conn.token_expiry < datetime.utcnow():
        conn.is_active = False
        db.commit()
        return {"status": "expired", "connection": None}
    return {
        "status": "connected",
        "connection": InstagramConnectionOut.model_validate(conn),
    }


@router.post("/disconnect", response_model=MessageOut)
def disconnect(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conn = db.query(InstagramConnection).filter(
        InstagramConnection.user_id == current_user.id
    ).first()
    if conn:
        conn.is_active = False
        conn.access_token_encrypted = ""  # wipe token
        db.commit()
    return {"message": "Instagram disconnected"}

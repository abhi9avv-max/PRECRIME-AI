"""API endpoints for third-party SIEM integration tests."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import AuditEvent
from app.schemas import WazuhTestResponse
from app.adapters.wazuh import test_wazuh_connection

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.post("/wazuh/test", response_model=WazuhTestResponse)
def test_wazuh_endpoint(db: Session = Depends(get_db)):
    """Test live authentication connectivity to Wazuh SIEM API.

    Does not modify any external configuration or store credentials.
    """
    res = test_wazuh_connection()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Record audit event for integration test
    audit = AuditEvent(
        id=str(uuid.uuid4()),
        investigation_id="system-integration",
        actor="analyst",
        action="WAZUH_CONNECTION_TESTED",
        timestamp=now_iso,
        details={"connected": res["connected"], "message": res["message"]},
    )
    db.add(audit)
    db.commit()

    return res

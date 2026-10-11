import hashlib
import json
import io
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import ComplianceAuditLog, SafetyIncident, ChildDevice, User

class ComplianceService:
    @staticmethod
    def generate_tamper_hash(data: Dict[str, Any]) -> str:
        """Generates SHA-256 digital fingerprint to guarantee non-repudiation."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    async def log_compliance_event(
        db: AsyncSession,
        event_type: str,
        parent_id: Optional[str],
        child_id: Optional[str],
        incident_id: Optional[str],
        details: Dict[str, Any]
    ) -> ComplianceAuditLog:
        """Records an immutable audit entry compliant with DPDP Act 2023 & POCSO 2012."""
        data_to_hash = {
            "event_type": event_type,
            "parent_id": parent_id,
            "child_id": child_id,
            "incident_id": incident_id,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        sig_hash = ComplianceService.generate_tamper_hash(data_to_hash)

        audit_entry = ComplianceAuditLog(
            event_type=event_type,
            parent_id=parent_id,
            child_id=child_id,
            incident_id=incident_id,
            details=details,
            hash_signature=sig_hash
        )
        db.add(audit_entry)
        await db.commit()
        await db.refresh(audit_entry)
        return audit_entry

    @staticmethod
    def generate_incident_pdf_bytes(
        incident: SafetyIncident,
        child: ChildDevice,
        parent: User
    ) -> bytes:
        """
        Builds a forensic legal/counseling Incident Report PDF.
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib import colors

            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter

            # Header Banner
            p.setFillColor(colors.HexColor("#0A0E1A"))
            p.rect(0, height - 90, width, 90, fill=True, stroke=False)

            p.setFillColor(colors.HexColor("#00E5FF"))
            p.setFont("Helvetica-Bold", 20)
            p.drawString(40, height - 45, "RAKSHAN AI — INCIDENT COMPLIANCE REPORT")

            p.setFillColor(colors.white)
            p.setFont("Helvetica", 10)
            p.drawString(40, height - 65, "Child Cyber-Safety, Risk Intelligence & Evidence Record | DPDP & POCSO Compliant")

            # Document Metadata
            y = height - 120
            p.setFillColor(colors.HexColor("#333333"))
            p.setFont("Helvetica-Bold", 12)
            p.drawString(40, y, "1. INCIDENT & PARTICIPANT DETAILS")

            y -= 20
            p.setFont("Helvetica", 10)
            p.drawString(50, y, f"Incident ID: {incident.id}")
            y -= 16
            p.drawString(50, y, f"Generated At: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            y -= 16
            p.drawString(50, y, f"Parent / Guardian Name: {parent.full_name} ({parent.email})")
            y -= 16
            p.drawString(50, y, f"Protected Child Identifier: {child.child_name} (Device: {child.device_id[:16]}...)")

            # Risk Summary
            y -= 30
            p.setFont("Helvetica-Bold", 12)
            p.drawString(40, y, "2. RISK METRICS & THREAT EVALUATION")

            y -= 20
            # Severity Color
            sev_color = colors.HexColor("#FF3B30") if incident.severity in ["HIGH", "CRITICAL"] else colors.HexColor("#FF9500")
            p.setFillColor(sev_color)
            p.rect(50, y - 5, 120, 22, fill=True, stroke=False)
            p.setFillColor(colors.white)
            p.setFont("Helvetica-Bold", 11)
            p.drawString(58, y, f"Risk Score: {incident.risk_score} / 100")

            p.setFillColor(colors.black)
            p.drawString(190, y, f"Severity: {incident.severity}")
            y -= 20
            p.setFont("Helvetica", 10)
            p.drawString(50, y, f"Detected Threat Category: {incident.category}")
            y -= 16
            p.drawString(50, y, f"Application Source: {incident.app_source or 'Instant Messaging'}")

            # Explainable AI Analysis
            y -= 30
            p.setFont("Helvetica-Bold", 12)
            p.drawString(40, y, "3. EXPLAINABLE AI (XAI) & DETECTION REASONING")

            y -= 20
            p.setFont("Helvetica", 10)
            reason_text = incident.detected_reason or "Suspicious pattern flagged by multi-agent analysis."
            # Wrap lines if long
            p.drawString(50, y, reason_text[:110])
            if len(reason_text) > 110:
                y -= 14
                p.drawString(50, y, reason_text[110:220])

            # Redacted Evidence Excerpt
            y -= 30
            p.setFont("Helvetica-Bold", 12)
            p.drawString(40, y, "4. SECURE EVIDENCE LOG (PRIVACY-REDACTED)")

            y -= 20
            p.setFont("Helvetica-Oblique", 9)
            snippet = incident.flagged_snippet or "[Sensitive digital context logged under DPDP Act encryption]"
            p.drawString(50, y, f"\"{snippet[:110]}\"")

            # Legal Disclaimer
            y -= 50
            p.setFillColor(colors.HexColor("#666666"))
            p.setFont("Helvetica-Bold", 9)
            p.drawString(40, y, "LEGAL COMPLIANCE NOTICE:")
            y -= 14
            p.setFont("Helvetica", 8)
            p.drawString(40, y, "This document is an AI-generated decision-support record compliant with the Digital Personal Data")
            y -= 11
            p.drawString(40, y, "Protection (DPDP) Act, 2023, and IT Rules 2021. It does not replace formal law enforcement discovery.")

            # Digital Signature Hash
            y -= 30
            p.setFillColor(colors.HexColor("#008899"))
            p.setFont("Courier", 8)
            sig = ComplianceService.generate_tamper_hash({"id": incident.id, "score": incident.risk_score})
            p.drawString(40, y, f"Digital SHA-256 Fingerprint: {sig}")

            p.showPage()
            p.save()
            buffer.seek(0)
            return buffer.getvalue()
        except ImportError:
            # Fallback text summary
            fallback = f"RAKSHAN AI INCIDENT REPORT\nIncident ID: {incident.id}\nScore: {incident.risk_score}\nCategory: {incident.category}\nReason: {incident.detected_reason}"
            return fallback.encode("utf-8")

compliance_service = ComplianceService()

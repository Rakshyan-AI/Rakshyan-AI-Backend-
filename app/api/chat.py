from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import ChatMessageRequest, ChatMessageResponse, HelplineInfo
from app.services.groq_service import groq_service

router = APIRouter(prefix="/chat", tags=["AI Legal & Child Safety Chatbot"])

@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(req: ChatMessageRequest):
    """
    Sends a query to Groq LLaMA configured with Indian Child Safety & Parental Monitoring Law expertise.
    Falls back gracefully to embedded knowledge base if offline or key is unconfigured.
    """
    if not req.message or not req.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat message cannot be empty."
        )

    history_payload = None
    if req.history:
        history_payload = [{"role": h.role, "content": h.content} for h in req.history]

    result = await groq_service.generate_chat_reply(
        user_message=req.message.strip(),
        history=history_payload,
        child_context=req.child_context
    )

    helplines_data = [
        HelplineInfo(name=h["name"], number=h["number"], purpose=h["purpose"])
        for h in result.get("helplines", [])
    ]

    return ChatMessageResponse(
        reply=result["reply"],
        model=result["model"],
        provider=result.get("provider", "Groq LLaMA"),
        relevant_laws=result.get("relevant_laws", []),
        helplines=helplines_data,
        suggested_actions=result.get("suggested_actions", []),
        action_command=result.get("action_command"),
        child_telemetry=result.get("child_telemetry"),
        success=result.get("success", True)
    )

@router.get("/quick-topics")
async def get_quick_topics():
    """Returns curated quick query topics for parent/child legal queries."""
    return {
        "topics": [
            {
                "id": "legality",
                "chip": "⚖️ Legality of Monitoring",
                "prompt": "Is it legal for parents to monitor their child's smartphone in India under DPDP Act 2023?"
            },
            {
                "id": "pocso",
                "chip": "🚨 POCSO & Grooming",
                "prompt": "What does POCSO Act say about online grooming and sending illicit messages to minors?"
            },
            {
                "id": "extortion",
                "chip": "💸 Hinglish Blackmail & Extortion",
                "prompt": "Someone is blackmailing my child online demanding money/photos. What immediate legal steps should I take?"
            },
            {
                "id": "cyberbullying",
                "chip": "⚠️ Cyberbullying Laws",
                "prompt": "What are the legal punishments for school cyberbullying and online harassment in India?"
            },
            {
                "id": "helplines",
                "chip": "📞 Emergency Helplines",
                "prompt": "What are the national child helpline and cyber crime reporting numbers in India?"
            },
            {
                "id": "dpdp",
                "chip": "🛡️ DPDP Child Consent Rules",
                "prompt": "How does DPDP Act 2023 protect children's personal data and online privacy?"
            }
        ]
    }

@router.get("/status")
async def get_chat_status():
    """Returns the Groq LLaMA configuration status."""
    return {
        "status": "online",
        "groq_configured": groq_service.is_configured(),
        "model": groq_service.model,
        "capabilities": [
            "POCSO Act 2012 guidance",
            "DPDP Act 2023 compliance",
            "IT Act 2000 & 67B provisions",
            "Parental monitoring fiduciary rights",
            "Real-time cyber extortion & grooming mitigation",
            "Hinglish / Hindi vernacular comprehension",
            "Emergency 1098 & 1930 dispatch coordination"
        ]
    }

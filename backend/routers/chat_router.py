import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from backend.auth import get_current_user
from backend.database import get_supabase_admin
from backend.services.rag_service import rag_service

router = APIRouter(prefix="/chat", tags=["AI Chat / RAG"])

class AskQuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question to query knowledge base")
    conversation_id: Optional[str] = Field(None, description="Optional conversation UUID")
    gemini_api_key: Optional[str] = Field(None, description="Optional custom Gemini API key")

class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"

@router.post("/ask")
async def ask_question(
    payload: AskQuestionRequest,
    user: dict = Depends(get_current_user)
):
    """
    RAG Endpoint:
    1. Embeds question
    2. Retrieves top relevant chunks from user's documents
    3. Prompts Gemini with strict grounding instructions
    4. Records messages and citations
    5. Returns answer with source citations
    """
    user_id = user["id"]
    question = payload.question.strip()
    admin = get_supabase_admin()

    # 1. Ensure Conversation exists
    conversation_id = payload.conversation_id
    if not conversation_id:
        # Create a new conversation with title based on first question
        conv_title = (question[:45] + "...") if len(question) > 45 else question
        new_conv_id = str(uuid.uuid4())
        try:
            admin.table("conversations").insert({
                "id": new_conv_id,
                "user_id": user_id,
                "title": conv_title
            }).execute()
            conversation_id = new_conv_id
        except Exception as e:
            print(f"[ChatRouter] Conversation creation error: {e}")
            conversation_id = str(uuid.uuid4())
    else:
        # Verify ownership of requested conversation
        conv_check = admin.table("conversations").select("id").eq("id", conversation_id).eq("user_id", user_id).execute()
        if not conv_check.data:
            # If not found or not owned, create a fresh one
            conversation_id = str(uuid.uuid4())
            admin.table("conversations").insert({
                "id": conversation_id,
                "user_id": user_id,
                "title": (question[:45] + "...") if len(question) > 45 else question
            }).execute()

    # 2. Fetch past conversation history (up to last 6 messages)
    history = []
    try:
        past_msgs = admin.table("messages") \
            .select("role, content") \
            .eq("conversation_id", conversation_id) \
            .eq("user_id", user_id) \
            .order("created_at", desc=False) \
            .limit(6) \
            .execute()
        if past_msgs.data:
            history = past_msgs.data
    except Exception as e:
        print(f"[ChatRouter] History fetch warning: {e}")

    # 3. Store user message in DB
    user_msg_id = str(uuid.uuid4())
    try:
        admin.table("messages").insert({
            "id": user_msg_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": "user",
            "content": question,
            "sources": []
        }).execute()
    except Exception as e:
        print(f"[ChatRouter] User message store warning: {e}")

    # 4. Execute RAG retrieval and answer synthesis
    rag_result = rag_service.answer_question(
        question=question,
        user_id=user_id,
        conversation_history=history,
        gemini_api_key=payload.gemini_api_key
    )

    answer_text = rag_result.get("answer", "")
    sources = rag_result.get("sources", [])

    # 5. Store assistant message with sources in DB
    assistant_msg_id = str(uuid.uuid4())
    try:
        admin.table("messages").insert({
            "id": assistant_msg_id,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": "assistant",
            "content": answer_text,
            "sources": sources
        }).execute()
    except Exception as e:
        print(f"[ChatRouter] Assistant message store warning: {e}")

    return {
        "conversation_id": conversation_id,
        "message_id": assistant_msg_id,
        "question": question,
        "answer": answer_text,
        "sources": sources
    }

@router.get("/conversations")
async def list_conversations(user: dict = Depends(get_current_user)):
    """
    Returns all conversations belonging to the authenticated user.
    """
    user_id = user["id"]
    admin = get_supabase_admin()

    try:
        res = admin.table("conversations") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("updated_at", desc=True) \
            .execute()
        return {"conversations": res.data or []}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch conversations: {str(e)}"
        )

@router.post("/conversations")
async def create_conversation(
    payload: CreateConversationRequest,
    user: dict = Depends(get_current_user)
):
    """
    Creates a new conversation thread.
    """
    user_id = user["id"]
    admin = get_supabase_admin()
    conv_id = str(uuid.uuid4())
    title = payload.title or "New Conversation"

    try:
        res = admin.table("conversations").insert({
            "id": conv_id,
            "user_id": user_id,
            "title": title
        }).execute()
        return {"conversation": res.data[0] if res.data else {"id": conv_id, "title": title}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")

@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Retrieves chronological message history for a conversation.
    Validates user ownership.
    """
    user_id = user["id"]
    admin = get_supabase_admin()

    # Check conversation ownership
    conv_res = admin.table("conversations").select("id, title").eq("id", conversation_id).eq("user_id", user_id).execute()
    if not conv_res.data:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied.")

    try:
        msgs_res = admin.table("messages") \
            .select("*") \
            .eq("conversation_id", conversation_id) \
            .eq("user_id", user_id) \
            .order("created_at", desc=False) \
            .execute()
        return {
            "conversation": conv_res.data[0],
            "messages": msgs_res.data or []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load messages: {str(e)}")

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Deletes conversation and associated messages.
    """
    user_id = user["id"]
    admin = get_supabase_admin()

    # Check ownership
    conv_res = admin.table("conversations").select("id").eq("id", conversation_id).eq("user_id", user_id).execute()
    if not conv_res.data:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    try:
        admin.table("conversations").delete().eq("id", conversation_id).eq("user_id", user_id).execute()
        return {"success": True, "message": "Conversation deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")

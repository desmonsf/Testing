# =====================================
# app/main.py
# =====================================
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
import os
from dotenv import load_dotenv
from .database import init_db
from .whatsapp import WhatsAppHandler
from .ai_coach import FacturationCoach
from .database import get_db_sync
import logging

# Configuration
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Coach Facturation IA",
    description="Assistant WhatsApp pour la gestion de facturation",
    version="1.0.0"
)

# Initialize services
whatsapp_handler = WhatsAppHandler()
ai_coach = FacturationCoach()

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("Application démarrée - Base de données initialisée")

@app.get("/")
async def webhook_verify_and_home(request: Request):
    """Vérification webhook WhatsApp + Page d'accueil"""
    
    # Vérifier si c'est une vérification webhook WhatsApp
    query_params = request.query_params
    mode = query_params.get("hub.mode")
    token = query_params.get("hub.verify_token") 
    challenge = query_params.get("hub.challenge")
    
    # Si c'est une vérification webhook
    if mode == "subscribe" and token == os.getenv("WHATSAPP_VERIFY_TOKEN"):
        logger.info("Webhook WhatsApp vérifié avec succès")
        return PlainTextResponse(challenge)
    
    # Sinon, page d'accueil normale
    return JSONResponse({
        "message": "Coach Facturation IA - API opérationnelle",
        "status": "actif",
        "service": "facturation-coach"
    })

@app.post("/")
async def webhook_message_handler(request: Request):
    """Traitement des messages WhatsApp"""
    try:
        webhook_data = await request.json()
        logger.info(f"Message WhatsApp reçu: {webhook_data}")
        
        parsed_message = whatsapp_handler.parse_webhook_message(webhook_data)
        
        if not parsed_message:
            logger.info("Pas de message à traiter")
            return PlainTextResponse("OK", status_code=200)
        
        user_phone = parsed_message["from"]
        message_body = parsed_message["body"]
        media_url = parsed_message["media_url"]
        
        logger.info(f"Message reçu de {user_phone}: {message_body}")
        
        # Traiter le message avec l'IA
        response_message = await ai_coach.process_message(
            user_phone=user_phone,
            message=message_body,
            media_url=media_url
        )
        
        # Envoyer la réponse
        await whatsapp_handler.send_message(
            to=user_phone,
            message=response_message
        )
        
        logger.info(f"Réponse envoyée à {user_phone}")
        return PlainTextResponse("OK", status_code=200)
        
    except Exception as e:
        logger.error(f"Erreur webhook WhatsApp: {str(e)}")
        return PlainTextResponse("Error", status_code=500)

@app.get("/health")
async def health_check():
    """Endpoint de santé pour UptimeRobot"""
    return JSONResponse({
        "status": "healthy", 
        "service": "facturation-coach",
        "message": "Service opérationnel"
    })

@app.head("/health")
async def health_head():
    return PlainTextResponse("", status_code=200)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )

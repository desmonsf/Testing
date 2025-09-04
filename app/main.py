# =====================================
# app/main.py
# =====================================
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
import os
from dotenv import load_dotenv
from .database import init_db
from .whatsapp import WhatsAppHandler
from .ai_coach import FacturationCoach
from .scheduler import SleepScheduler
from .models import PendingMessage
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
sleep_scheduler = SleepScheduler()

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("Application démarrée - Base de données initialisée")

@app.middleware("http")
async def sleep_middleware(request, call_next):
    """Middleware pour gérer les horaires de veille"""
    # Exceptions: santé et vérification webhook
    if request.url.path in ["/health"] or (
        request.url.path == "/webhook/whatsapp" and request.method == "GET"
    ):
        return await call_next(request)
    
    # Vérifier si c'est l'heure de veille
    if sleep_scheduler.is_sleep_time():
        if request.url.path == "/webhook/whatsapp" and request.method == "POST":
            # Stocker le message pour traitement au réveil
            try:
                webhook_data = await request.json()
                parsed_message = whatsapp_handler.parse_webhook_message(webhook_data)
                
                if parsed_message:
                    db = get_db_sync()
                    pending = PendingMessage(
                        user_phone=parsed_message["from"],
                        message=parsed_message["body"],
                        media_url=parsed_message["media_url"]
                    )
                    db.add(pending)
                    db.commit()
                    db.close()
                    
                    # Envoyer message de veille
                    await whatsapp_handler.send_message(
                        to=parsed_message["from"],
                        message=sleep_scheduler.get_sleep_message()
                    )
                    
                logger.info("Message stocké pour traitement au réveil")
            except Exception as e:
                logger.error(f"Erreur stockage message: {str(e)}")
            
            return PlainTextResponse("OK", status_code=200)
        else:
            raise HTTPException(
                status_code=503, 
                detail="Service en pause nocturne. Actif de 8h à minuit."
            )
    
    return await call_next(request)

@app.get("/")
async def root():
    return {
        "message": "Coach Facturation IA - API opérationnelle",
        "status": "veille" if sleep_scheduler.is_sleep_time() else "actif",
        "horaires": "8h - 00h (heure française)"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "facturation-coach",
        "time": "veille" if sleep_scheduler.is_sleep_time() else "actif"
    }

@app.get("/webhook/whatsapp")
async def whatsapp_webhook_verify(request: Request):
    """Vérification du webhook WhatsApp Cloud API"""
    query_params = request.query_params
    mode = query_params.get("hub.mode")
    token = query_params.get("hub.verify_token") 
    challenge = query_params.get("hub.challenge")
    
    challenge_response = whatsapp_handler.verify_webhook(mode, token, challenge)
    
    if challenge_response:
        logger.info("Webhook WhatsApp vérifié avec succès")
        return PlainTextResponse(challenge_response)
    else:
        logger.warning("Échec vérification webhook WhatsApp")
        raise HTTPException(status_code=403, detail="Forbidden")

@app.post("/webhook/whatsapp")
async def whatsapp_webhook_message(request: Request):
    """Webhook WhatsApp Cloud API - Traitement des messages"""
    try:
        webhook_data = await request.json()
        logger.info(f"Webhook reçu: {webhook_data}")
        
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )

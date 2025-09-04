# =====================================
# app/whatsapp.py
# =====================================
import os
import requests
from typing import Optional
import logging
import json

logger = logging.getLogger(__name__)

class WhatsAppHandler:
    def __init__(self):
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.business_account_id = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
        
        self.base_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}"
        
        if not all([self.access_token, self.phone_number_id]):
            logger.warning("Configuration WhatsApp Cloud API incomplète")
    
    async def send_message(self, to: str, message: str) -> bool:
        """Envoie un message WhatsApp via Cloud API"""
        if not self.access_token:
            logger.error("Token WhatsApp non configuré")
            return False
        
        clean_to = to.replace("whatsapp:", "").replace("+", "")
            
        url = f"{self.base_url}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": clean_to,
            "type": "text",
            "text": {"body": message}
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Message envoyé - ID: {result.get('messages', [{}])[0].get('id', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi WhatsApp: {str(e)}")
            return False
    
    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """Vérifie le webhook WhatsApp lors de la configuration"""
        if mode == "subscribe" and token == self.verify_token:
            logger.info("Webhook WhatsApp vérifié avec succès")
            return challenge
        else:
            logger.warning("Échec vérification webhook WhatsApp")
            return None
    
    def parse_webhook_message(self, webhook_data: dict) -> Optional[dict]:
        """Parse les données du webhook WhatsApp"""
        try:
            entry = webhook_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            
            messages = value.get("messages")
            if not messages:
                return None
                
            message = messages[0]
            
            parsed_data = {
                "message_id": message.get("id"),
                "from": message.get("from"),
                "timestamp": message.get("timestamp"),
                "type": message.get("type"),
                "body": "",
                "media_url": None
            }
            
            if message.get("type") == "text":
                parsed_data["body"] = message.get("text", {}).get("body", "")
            elif message.get("type") == "image":
                parsed_data["media_url"] = message.get("image", {}).get("id")
                parsed_data["body"] = message.get("image", {}).get("caption", "")
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Erreur parsing webhook: {str(e)}")
            return None

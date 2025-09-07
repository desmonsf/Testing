# =====================================
# app/whatsapp.py
# =====================================
import os
import requests
from typing import Optional
import logging
import json
import hashlib  # <-- LOG: pour empreinte du token

logger = logging.getLogger(__name__)

class WhatsAppHandler:
    def __init__(self):
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.business_account_id = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
        
        # NOTE: on garde ta version actuelle (v18.0), on la log juste
        self.base_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}"
        
        if not all([self.access_token, self.phone_number_id]):
            logger.warning("Configuration WhatsApp Cloud API incomplète")
        else:
            # LOG: infos de démarrage utiles
            token_preview = self.access_token or ""
            fp = hashlib.sha256(token_preview.encode()).hexdigest()[:10]
            has_ws = (token_preview != token_preview.strip())
            logger.info(
                "[WA:init] phone_number_id=%s | base_url=%s | token_len=%d | token_fp=%s | token_prefix=%s | token_has_leading_trailing_ws=%s",
                self.phone_number_id, self.base_url, len(token_preview), fp, token_preview[:3], has_ws
            )
            if has_ws or token_preview.endswith("\n"):
                logger.warning("[WA:init] Le token semble contenir des espaces ou des retours de ligne en bordure")

            if "v18.0" in self.base_url:
                logger.info("[WA:init] API version détectée: v18.0 (simplement informatif)")

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

        # LOG: avant l’appel
        logger.info("[WA:send] POST %s | to_raw=%s | to_clean=%s", url, to, clean_to)
        logger.debug("[WA:send] payload=%s", json.dumps(data, ensure_ascii=False))

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)

            # LOG: on trace toujours le statut + corps (utile pour 401/4xx)
            try:
                body_text = response.text
            except Exception:
                body_text = "<no-text>"

            logger.info("[WA:send] status=%s", response.status_code)
            logger.debug("[WA:send] response_body=%s", body_text)

            # si erreur HTTP, on logge le corps exact avant de raise
            if not response.ok:
                logger.error("[WA:send] HTTP error body: %s", body_text)
                response.raise_for_status()

            result = response.json()
            logger.info(
                "Message envoyé - ID: %s",
                result.get('messages', [{}])[0].get('id', 'unknown')
            )
            return True

        except requests.HTTPError as e:
            # LOG: détaille code + contenu
            status = getattr(e.response, "status_code", "unknown")
            text = getattr(e.response, "text", str(e))
            logger.error("[WA:send] HTTPError status=%s body=%s", status, text)
            return False
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
            # LOG: trace les principaux champs reçus
            logger.debug("[WA:webhook] payload_brut_keys=%s", list(webhook_data.keys()))

            entry = webhook_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            
            messages = value.get("messages")
            if not messages:
                # LOG: utile pour différencier 'statuses' vs 'messages'
                logger.info("[WA:webhook] pas de 'messages' (peut être un status). value_keys=%s", list(value.keys()))
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

            # LOG: résumé du message parsé
            logger.info("[WA:webhook] parsed from=%s type=%s body_len=%d", parsed_data["from"], parsed_data["type"], len(parsed_data["body"] or ""))

            return parsed_data
            
        except Exception as e:
            logger.error(f"Erreur parsing webhook: {str(e)}")
            return None

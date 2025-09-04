# =====================================
# app/ai_coach.py
# =====================================
import os
import openai
from typing import Optional
import logging
from datetime import datetime, timedelta
from .database import get_db_sync
from .models import User, Invoice, Conversation, PendingMessage
import json
import re

logger = logging.getLogger(__name__)

class FacturationCoach:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
        else:
            logger.warning("Clé API OpenAI non configurée")
    
    async def process_message(self, user_phone: str, message: str, media_url: Optional[str] = None) -> str:
        """Traite un message utilisateur et génère une réponse de coaching"""
        try:
            db = get_db_sync()
            
            # Obtenir ou créer l'utilisateur
            user = self._get_or_create_user(db, user_phone)
            
            # Mettre à jour la dernière activité
            user.last_active = datetime.now()
            db.commit()
            
            # Analyser le message
            message_intent = self._analyze_message_intent(message)
            
            # Générer la réponse selon l'intention
            if message_intent == "greeting":
                response = self._handle_greeting(user, message)
            elif message_intent == "invoice_help":
                response = self._handle_invoice_help(user, message)
            elif message_intent == "payment_reminder":
                response = self._handle_payment_reminder(user, message)
            elif message_intent == "business_advice":
                response = self._handle_business_advice(user, message)
            elif media_url:
                response = await self._handle_invoice_image(user, message, media_url)
            else:
                response = self._handle_general_question(user, message)
            
            # Sauvegarder la conversation
            conversation = Conversation(
                user_phone=user_phone,
                message=message,
                response=response,
                message_type="image" if media_url else "text"
            )
            db.add(conversation)
            db.commit()
            db.close()
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur traitement message: {str(e)}")
            return "Désolé, j'ai rencontré un problème technique. Pouvez-vous réessayer ?"
    
    def _get_or_create_user(self, db, phone: str) -> User:
        """Obtient ou crée un utilisateur"""
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            user = User(phone=phone, business_type="unknown")
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    
    def _analyze_message_intent(self, message: str) -> str:
        """Analyse l'intention du message"""
        message_lower = message.lower()
        
        greeting_patterns = ["salut", "bonjour", "bonsoir", "hello", "coucou", "hey"]
        invoice_patterns = ["facture", "devis", "facturation", "client", "paiement", "relance"]
        reminder_patterns = ["rappel", "relance", "retard", "impayé", "relancer"]
        advice_patterns = ["conseil", "aide", "comment", "que faire", "stratégie"]
        
        if any(pattern in message_lower for pattern in greeting_patterns):
            return "greeting"
        elif any(pattern in message_lower for pattern in reminder_patterns):
            return "payment_reminder"
        elif any(pattern in message_lower for pattern in invoice_patterns):
            return "invoice_help"
        elif any(pattern in message_lower for pattern in advice_patterns):
            return "business_advice"
        else:
            return "general"
    
    def _handle_greeting(self, user: User, message: str) -> str:
        """Gère les messages de salutation"""
        current_hour = datetime.now().hour
        
        if current_hour < 12:
            greeting = "Bonjour"
        elif current_hour < 18:
            greeting = "Bon après-midi"
        else:
            greeting = "Bonsoir"
        
        if not user.name:
            return f"""👋 {greeting} ! Je suis ton coach facturation IA !

Je suis là pour t'aider à :
• 📋 Suivre tes factures et relances
• 💡 Te donner des conseils de facturation
• ⏰ Te rappeler les échéances importantes
• 📈 Améliorer ta gestion commerciale

Pour commencer, dis-moi ton prénom et ton activité (ex: "Je m'appelle Marie, je suis graphiste freelance")"""
        else:
            return f"""{greeting} {user.name} ! 👋

Comment puis-je t'aider aujourd'hui ?
• Envoie-moi une photo de facture pour l'analyser
• Pose-moi une question sur la facturation
• Demande-moi des conseils de relance

Que veux-tu faire ?"""
    
    def _handle_invoice_help(self, user: User, message: str) -> str:
        """Gère les questions sur la facturation"""
        prompt = f"""Tu es un expert-comptable bienveillant qui conseille un entrepreneur.

Contexte utilisateur:
- Activité: {user.business_type or 'indépendant'}
- Message: "{message}"

Donne un conseil pratique et actionnable sur la facturation en maximum 200 mots.
Sois chaleureux, professionnel et donne des exemples concrets.
"""
        
        try:
            if self.openai_api_key:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                    temperature=0.7
                )
                return response.choices[0].message.content.strip()
            else:
                return self._get_default_invoice_advice()
        except Exception as e:
            logger.error(f"Erreur OpenAI: {str(e)}")
            return self._get_default_invoice_advice()
    
    def _handle_payment_reminder(self, user: User, message: str) -> str:
        """Gère les questions sur les relances"""
        return """💪 Voici ma stratégie de relance efficace :

**J+7 après échéance - Relance douce :**
"Bonjour, j'espère que tout va bien. Je me permets de vous rappeler que la facture n°XXX était due le XX/XX. Pourriez-vous me confirmer le règlement ? Merci !"

**J+15 - Relance ferme :**
"Bonjour, la facture n°XXX reste impayée depuis 15 jours. Merci de procéder au règlement sous 48h ou de m'indiquer la date prévue."

**J+30 - Relance finale :**
"Dernière relance avant mise en demeure. Facture n°XXX impayée depuis 1 mois. Règlement exigé sous 8 jours."

💡 **Astuce :** Toujours rester professionnel et garder une trace écrite !

Veux-tu que je t'aide à rédiger une relance spécifique ?"""
    
    def _handle_business_advice(self, user: User, message: str) -> str:
        """Gère les demandes de conseils business"""
        conseils = [
            "💰 Fixe toujours un acompte de 30-50% avant de commencer",
            "📅 Facture dès la livraison, ne pas attendre",
            "⚡ Propose un escompte pour paiement comptant (2% à 8 jours)",
            "📋 Utilise des conditions de vente claires sur tes devis",
            "🔄 Fais du suivi client régulier, pas que pour les impayés"
        ]
        
        import random
        conseil_du_jour = random.choice(conseils)
        
        return f"""🎯 **Conseil du jour :**
{conseil_du_jour}

💡 **Question pour toi :** Quel est ton plus gros défi en facturation actuellement ?

Dis-moi en quelques mots et je te donnerai des conseils personnalisés !"""
    
    async def _handle_invoice_image(self, user: User, message: str, media_url: str) -> str:
        """Gère l'analyse d'images de factures"""
        return """📸 J'ai bien reçu ton image !

🔄 **Analyse en cours...** (fonctionnalité bientôt disponible)

En attendant, peux-tu me dire :
• Le montant de cette facture ?
• La date d'échéance ?
• Le nom du client ?

Je pourrai t'aider à planifier tes relances ! 👍"""
    
    def _handle_general_question(self, user: User, message: str) -> str:
        """Gère les questions générales"""
        return """🤔 Je suis spécialisé dans la facturation et la gestion commerciale.

Je peux t'aider avec :
• ✅ Conseils de facturation
• ✅ Stratégies de relance
• ✅ Conditions de vente
• ✅ Suivi de trésorerie
• ✅ Analyse de factures (bientôt)

Pose-moi une question plus précise sur ces sujets ! 💪"""
    
    def _get_default_invoice_advice(self) -> str:
        """Conseil par défaut si l'IA n'est pas disponible"""
        return """💡 **Conseil facturation :**

Les bases d'une bonne facture :
• ✅ Numéro unique et chronologique
• ✅ Tes informations complètes (SIRET, TVA)
• ✅ Date de facturation et d'échéance claire
• ✅ Détail des prestations
• ✅ Conditions de règlement

🎯 **Astuce pro :** Envoie toujours un accusé de réception et confirme la bonne réception de ta facture !

Une autre question ?"""

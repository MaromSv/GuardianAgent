# utils/alerts.py

import os
import logging
from twilio.rest import Client
import dotenv

dotenv.load_dotenv()

logger = logging.getLogger(__name__)

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM_NUMBER")
NUMBER_TO_SEND_SMS_TO = os.getenv("PROTECTED_USER_NUMBER_2")

client = Client(TWILIO_SID, TWILIO_AUTH)


def send_family_alert_sms(
    family_number: str, user_number: str, scam_details: str, risk_score: float
):
    """
    Sends an SMS alert to a family member warning that the user may have been targeted by a scam call.
    """

    message_body = (
        f"Your Family Member with number: {user_number} may have been targeted by a scam call.\n"
        f"Risk Score: {risk_score}%\n\n"
        f"Details: {scam_details}\n\n"
        f"Guardian Agent has reported the scammer and likely protected them, "
        f"but please reach out to make sure they are okay and did not share information."
    )

    try:
        client.messages.create(
            body=message_body,
            from_=TWILIO_FROM,
            to=family_number,
        )
        return {"success": True, "sent_to": family_number}

    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Test the SMS function
    response = send_family_alert_sms(
        family_number=NUMBER_TO_SEND_SMS_TO,
        user_number=NUMBER_TO_SEND_SMS_TO,
        scam_details="Caller claimed to be from the bank and asked for your account info.",
        risk_score=92.5,
    )
    print(response)

from firebase_admin import messaging
import logging

logger = logging.getLogger(__name__)

def send_critical_alert(fcm_device_token, title, body, data_payload=None):
    """
    Sends an FCM push notification to the mobile app when a high-risk event is detected.
    """
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data_payload if data_payload else {},
            token=fcm_device_token,
        )
        
        response = messaging.send(message)
        logger.info(f"FCM Notification sent successfully: {response}")
        return True

    except Exception as e:
        logger.error(f"Failed to send FCM notification: {str(e)}")
        return False
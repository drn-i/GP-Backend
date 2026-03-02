from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from utils.mongo_client import get_mongo_db
from datetime import datetime, timezone

class VitalsIngestionView(APIView):
    """POST /api/v1/vitals/ -> n8n pushes data here"""
    permission_classes = [IsAuthenticated] 
    def post(self, request):
        db = get_mongo_db()
        payload = request.data

        records = payload if isinstance(payload, list) else [payload]  # Support both single object and list of objects
        
        insrted_ids = []
        alerts_triggered = 0
        #va
        # 1. Enforce that n8n includes the user_id (the Firebase UID)
        for record in records:
            user_id = record.get('user_id')
            # Security: Prevent a user from sending vitals for someone else
            if request.user.username != record['user_id']:
                return Response({"error": "Unauthorized data submission"}, status=status.HTTP_403_FORBIDDEN)
            if "user_id" not in record:
                return Response({"error": "Missing user_id in payload"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 2. Add a server-side timestamp so you always know exactly when it arrived
        for record in records:
            record['received_at'] = datetime.now(timezone.utc)
        
        # 3. Dump the raw JSON directly into MongoDB. 
        # No schema needed. If Amer changes the n8n output, this still works perfectly.
        result = db.vitals.insert_many(records)
        
        return Response({
            "status": "success", 
            "inserted_count": len(result.inserted_ids)
        }, status=status.HTTP_201_CREATED)

class LiveVitalsView(APIView):
    """GET /api/v1/vitals/live/{user_id}/ -> Mobile App polls this"""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        # Security: Prevent a user from fetching someone else's vitals
        if request.user.username != user_id:
             return Response({"error": "Unauthorized data access"}, status=status.HTTP_403_FORBIDDEN)

        db = get_mongo_db()
        
        # Fetch the single most recent document for this specific user
        latest_vital = db.vitals.find_one(
            {"user_id": user_id}, 
            sort=[("received_at", -1)] 
        )
        
        if not latest_vital:
            return Response({"error": "No vitals found for this user"}, status=status.HTTP_404_NOT_FOUND)
            
        # Fix the MongoDB ID: MongoDB uses an 'ObjectId' type which breaks JSON serialization.
        # We must convert it to a normal string before returning it to Khaled.
        latest_vital['_id'] = str(latest_vital['_id'])
        
        return Response(latest_vital, status=status.HTTP_200_OK)
    
class RiskResultIngestionView(APIView):
    """
    POST /api/v1/vitals/risk-results/
    Handles the 27-feature WESAD dataset payloads from the n8n pipeline.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        db = get_mongo_db()
        payload = request.data

        # n8n sends a list [ {...} ], but just in case it sends a single dict {...}
        # we standardize it into a list so our loop always works.
        records = payload if isinstance(payload, list) else [payload]
        
        inserted_ids = []
        alerts_triggered = 0

        for record in records:
            # 1. Validation: Ensure the Firebase UID (user_id) is present
            user_id = record.get("user_id")
            if not user_id:
                continue # Skip invalid records

            # 2. Add a server timestamp to track exactly when Django received it
            record['server_received_at'] = datetime.now(timezone.utc)

            # 3. Save the entire 27-feature dictionary into MongoDB
            result = db.risk_results.insert_one(record)
            inserted_ids.append(str(result.inserted_id))

            # 4. Push Notification Logic for Khaled's Mobile App
            risk_level = record.get("risk_level", "Low")
            
            if risk_level in ["High", "Critical"]:
                # TODO: In the future, fetch the user's FCM device token from your MySQL User model
                # fcm_token = get_user_fcm_token(user_id) 
                # send_critical_alert(
                #     fcm_token, 
                #     title=f"{risk_level} Stress Alert!", 
                #     body="Abnormal vitals detected. Please check the app."
                # )
                alerts_triggered += 1

        if not inserted_ids:
            return Response({"error": "No valid records provided"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "status": "success",
            "records_processed": len(inserted_ids),
            "alerts_triggered": alerts_triggered,
            "inserted_ids": inserted_ids
        }, status=status.HTTP_201_CREATED)
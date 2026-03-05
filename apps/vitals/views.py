from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from firebase_admin import messaging
from apps.profiles.models import MedicalProfile
from utils.mongo_client import get_mongo_db
from datetime import datetime, timezone

# Import the schema validator we just created
from .serializers import RiskResultSerializer

class VitalsIngestionView(APIView):
    """POST /api/v1/vitals/ -> raw vitals endpoint"""
    permission_classes = [IsAuthenticated] 
    
    def post(self, request):
        db = get_mongo_db()
        payload = request.data
        records = payload if isinstance(payload, list) else [payload]  
        
        for record in records:
            # Bug fix: Use .get() to prevent KeyError if user_id is missing entirely
            user_id = record.get('user_id')
            
            if not user_id:
                return Response({"error": "Missing user_id in payload"}, status=status.HTTP_400_BAD_REQUEST)
                
            # Security: Prevent a user from sending vitals for someone else
            if request.user.username != user_id and not request.user.is_staff:
                return Response({"error": "Unauthorized data submission"}, status=status.HTTP_403_FORBIDDEN)
        
        for record in records:
            record['received_at'] = datetime.now(timezone.utc)
        
        result = db.vitals.insert_many(records)
        
        return Response({
            "status": "success", 
            "inserted_count": len(result.inserted_ids)
        }, status=status.HTTP_201_CREATED)


class LiveVitalsView(APIView):
    """
    GET /api/live-vitals/{user_id}/?limit=30
    Returns an array of recent vitals to power the FlutterFlow's Live Data and Trends charts.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if request.user.username != user_id:
             return Response({"error": "Unauthorized data access"}, status=status.HTTP_403_FORBIDDEN)

        try: 
            limit = int(request.query_params.get('limit', 1))
        except ValueError:
            limit = 1

        db = get_mongo_db()
        
        cursor = db.risk_results.find(
            {"user_id": user_id}, 
            sort=[("server_received_at", -1)]
        ).limit(limit)

        results = list(cursor)
        
        # Format the Mongo IDs and return the array for the FlutterFlow graphs!
        for res in results:
            res['_id'] = str(res['_id'])
            
        return Response(results, status=status.HTTP_200_OK)  

class RiskResultIngestionView(APIView):
    """
    POST /api/v1/risk-results/
    Handles the 27-feature WESAD dataset payloads from the n8n pipeline.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payload = request.data
        records = payload if isinstance(payload, list) else [payload]
        
        # 1. Validation: Pass the data through our Serializer schema!
        serializer = RiskResultSerializer(data=records, many=True)
        if not serializer.is_valid():
            # If Amer sends bad data (like a string instead of a float), Django blocks it automatically
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 2. Get the clean, validated data
        valid_records = serializer.validated_data
        db = get_mongo_db()
        inserted_ids = []
        alerts_triggered = 0

        for record in valid_records:
            # Security: Ensure Firebase UID matches
            if request.user.username != record['user_id'] and not request.user.is_staff:
                return Response({"error": "Unauthorized data submission"}, status=status.HTTP_403_FORBIDDEN)

            record['server_received_at'] = datetime.now(timezone.utc)
            
            # Insert into MongoDB
            result = db.risk_results.insert_one(record)
            inserted_ids.append(str(result.inserted_id))

            # Push Notification Logic
            risk_level = record.get("risk_level", "Low")
            if risk_level in ["High", "Critical"]:
                alerts_triggered += 1

                try:
                    profile = MedicalProfile.objects.get(user__username=record['user_id'])
                    if profile.fcm_token:
                        message = messaging.Message(
                            notification=messaging.Notification(
                                title=f"Health Alert: {risk_level} Stress Alert Detected",
                                body=f"Your recent vitals indicate a {risk_level.lower()} physiological stress. Please check the app for your AI summary."
                            ),
                            token=profile.fcm_token,
                        )
                        response = messaging.send(message)
                        print(f"Successfully sent alert to {record['user_id']} with FCM token {response}")
                    else:
                        print(f"No FCM token found for user {record['user_id']}. Cannot send alert.")
                except MedicalProfile.DoesNotExist:
                    print(f"No medical profile found for user {record['user_id']}. Cannot send alert.")
                except Exception as e:
                    print(f"Firebase Push Failed: {str(e)}")

        return Response({
            "status": "success",
            "records_processed": len(inserted_ids),
            "alerts_triggered": alerts_triggered,
            "inserted_ids": inserted_ids
        }, status=status.HTTP_201_CREATED)


class RiskSummaryView(APIView):
    """
    GET /api/v1/summary/{user_id}/
    Fetches the historical risk results so Khaled can display them on mobile charts.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        # Security: Prevent a user from fetching someone else's history
        if request.user.username != user_id and not request.user.is_staff:
             return Response({"error": "Unauthorized data access"}, status=status.HTTP_403_FORBIDDEN)

        db = get_mongo_db()
        
        # Fetch the 10 most recent risk evaluations for the chart
        cursor = db.risk_results.find(
            {"user_id": user_id}, 
            sort=[("server_received_at", -1)] 
        ).limit(10)
        
        results = list(cursor)
        
        if not results:
            return Response({"message": "No risk history found"}, status=status.HTTP_404_NOT_FOUND)
            
        # Fix the MongoDB ID serialization issue
        for res in results:
            res['_id'] = str(res['_id'])
            
        return Response(results, status=status.HTTP_200_OK)
    

class AllRiskEventsView(APIView):
    """
    GET /api/risk-events/
    Fetches the latest risk events across ALL users for Eyad's Streamlit Dashboard.
    """
    permission_classes = [IsAuthenticated] 

    def get(self, request): 
        db = get_mongo_db()
        
        # Fetch the 50 most recent events across the entire system
        cursor = db.risk_results.find(
            {}, 
            sort=[("server_received_at", -1)] 
        ).limit(50)
        
        results = list(cursor)
        
        for res in results:
            res['_id'] = str(res['_id'])
            
        return Response(results, status=status.HTTP_200_OK) 
class MobileDashboardView(APIView):
    """
    GET /api/v1/vitals/dashboard/{user_id}/
    Provides a pre-calculated, lightweight summary specifically for the FlutterFlow Home Screen.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if request.user.username != user_id:
             return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        db = get_mongo_db()
        
        # 1. Get the single most recent AI Risk Result for the current status
        latest_result = db.risk_results.find_one(
            {"user_id": user_id}, 
            sort=[("server_received_at", -1)]
        )
        
        if not latest_result:
            return Response({
                "risk_rate": "N/A",
                "stress_level": "No Data",
                "average_hr": 0,
                "daily_summary": "Please wear your device to start collecting data."
            }, status=status.HTTP_200_OK)

        # 2. Get the last 10 readings to calculate the "Average HR" for the dashboard chart
        recent_cursor = db.risk_results.find(
            {"user_id": user_id}, 
            sort=[("server_received_at", -1)]
        ).limit(10)
        
        recent_results = list(recent_cursor)
        
        # Calculate the average HR from the recent features
        total_hr = sum(res.get('features', {}).get('hr_mean', 0) for res in recent_results)
        avg_hr = round(total_hr / len(recent_results)) if recent_results else 0

        # 3. Format the exact JSON payload Khaled needs for his UI
        dashboard_data = {
            "risk_rate": latest_result.get("risk_level", "Unknown"), 
            "stress_level": latest_result.get("risk_level", "Unknown"), # WESAD translates stress to risk
            "average_hr": avg_hr,
            "daily_summary": latest_result.get("summary", "No AI summary available yet."),
            "last_updated": latest_result.get("timestamp")
        }

        return Response(dashboard_data, status=status.HTTP_200_OK)
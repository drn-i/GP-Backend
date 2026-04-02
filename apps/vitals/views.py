from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from firebase_admin import messaging
from apps.profiles.models import MedicalProfile
from utils.mongo_client import get_mongo_db
from datetime import datetime, timezone, timedelta
# Serializer for validating incoming risk result data
from .serializers import RiskResultSerializer, Segment1ResultSerializer

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

# Segment 1 Result Ingestion View
class Segment1ResultIngestionView(APIView):
    """
    POST /api/segment1-results/
    Stores aligned Segment 1 inference results from Jetson/Runpod.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payload = request.data
        records = payload if isinstance(payload, list) else [payload]

        serializer = Segment1ResultSerializer(data=records, many=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        valid_records = serializer.validated_data
        db = get_mongo_db()
        inserted_ids = []

        for record in valid_records:
            if request.user.username != record["user_id"] and not request.user.is_staff:
                return Response({"error": "Unauthorized data submission"}, status=status.HTTP_403_FORBIDDEN)

            record["server_received_at"] = datetime.now(timezone.utc)
            result = db.segment1_results.insert_one(record)
            inserted_ids.append(str(result.inserted_id))

        return Response({
            "status": "success",
            "records_processed": len(inserted_ids),
            "inserted_ids": inserted_ids
        }, status=status.HTTP_201_CREATED)

# Segment 1 Result List View
class Segment1ResultListView(APIView):
    """
    GET /api/segment1-results/<user_id>/?limit=10
    Returns recent aligned Segment 1 results.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if request.user.username != user_id and not request.user.is_staff:
            return Response({"error": "Unauthorized data access"}, status=status.HTTP_403_FORBIDDEN)

        try:
            limit = int(request.query_params.get("limit", 10))
        except ValueError:
            limit = 10

        db = get_mongo_db()
        cursor = db.segment1_results.find(
            {"user_id": user_id},
            sort=[("server_received_at", -1)]
        ).limit(limit)

        results = list(cursor)
        for res in results:
            res["_id"] = str(res["_id"])

        return Response(results, status=status.HTTP_200_OK)

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


# -------------------------------------------------------------------
#  DEVICE MANAGEMENT API
# -------------------------------------------------------------------
class DeviceStatusView(APIView):
    """ GET /api/devices/status/{user_id}/ """
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if request.user.username != user_id:
             return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
             
        # Currently mocked for Khaled's UI. Later, Amer can POST actual battery life to the DB.
        return Response({
            "device_name": "EmotiBit Sensor",
            "battery_level": 75,
            "status": "Connected"
        }, status=status.HTTP_200_OK)


# -------------------------------------------------------------------
#  CHAT AGENT API
# -------------------------------------------------------------------
class SupportChatView(APIView):
    """ POST /api/support/chat/ """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_message = request.data.get("message", "").lower()
        
        # Smart Mock Agent for Khaled's UI testing
        reply = "I'm sorry, I didn't quite catch that. Could you provide more details?"
        if "order" in user_message or "tracking" in user_message:
            reply = "I'm sorry to hear your order is delayed! Let me look into that right away. Could you please share your order number?"
        elif "stress" in user_message or "heart" in user_message:
            reply = "I can help with your vitals. Make sure your EmotiBit sensor is connected and firmly placed on your wrist."

        return Response({"reply": reply}, status=status.HTTP_200_OK)


# -------------------------------------------------------------------
#  DAILY ANALYTICS API (Reports Dashboard)
# -------------------------------------------------------------------
class DailyAnalyticsView(APIView):
    """ GET /api/analytics/daily/{user_id}/?date=YYYY-MM-DD """
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if request.user.username != user_id:
             return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        target_date_str = request.query_params.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))
        db = get_mongo_db()
        
        # Search MongoDB for any records containing this exact date string in the timestamp
        cursor = db.risk_results.find({
            "user_id": user_id,
            "timestamp": {"$regex": f"^{target_date_str}"}
        })
        results = list(cursor)

        if not results:
             return Response({
                 "date": target_date_str,
                 "avg_hr": 0, "stress_level": "No Data", "activity_level": "No Data",
                 "summary": "No vitals recorded for this date."
             }, status=status.HTTP_200_OK)

        # Calculate averages for the day
        total_hr = sum(r.get('features', {}).get('hr_mean', 0) for r in results)
        avg_hr = int(total_hr / len(results))
        
        # Get the most common risk level for the day
        risk_levels = [r.get('risk_level', 'Low') for r in results]
        predominant_risk = max(set(risk_levels), key=risk_levels.count)

        return Response({
            "date": target_date_str,
            "avg_hr": avg_hr,
            "stress_level": predominant_risk,
            "activity_level": "Active" if avg_hr > 80 else "Normal",
            "summary": f"Your vitals were generally stable today with a predominant stress level of {predominant_risk}."
        }, status=status.HTTP_200_OK)


# -------------------------------------------------------------------
#  WEEKLY TRENDS API (Charts & Graphs)
# -------------------------------------------------------------------
class WeeklyAnalyticsView(APIView):
    """ GET /api/analytics/weekly/{user_id}/ """
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if request.user.username != user_id:
             return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        db = get_mongo_db()
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        # Get all records from the last 7 days
        cursor = db.risk_results.find({
            "user_id": user_id,
            "server_received_at": {"$gte": seven_days_ago}
        })
        results = list(cursor)

        # 1. Bar Chart Data (Events per day of the week)
        events_per_day = {"Mon": 0, "Tue": 0, "Wed": 0, "Thu": 0, "Fri": 0, "Sat": 0, "Sun": 0}
        
        # 2. Pie Chart Data (Count trigger types based on risk_level)
        triggers = {"Class Stress": 0, "Low Movement": 0, "Other": 0}

        for r in results:
            # Map the timestamp to a day of the week
            if 'server_received_at' in r:
                day_name = r['server_received_at'].strftime('%a') # Returns 'Mon', 'Tue', etc.
                if day_name in events_per_day:
                    events_per_day[day_name] += 1
            
            # Simple grouping logic for the Pie Chart based on AI risk levels
            risk = r.get("risk_level", "Low")
            if risk == "Critical":
                triggers["Class Stress"] += 1
            elif risk == "High":
                triggers["Low Movement"] += 1
            else:
                triggers["Other"] += 1

        return Response({
            "bar_chart_data": events_per_day,
            "pie_chart_data": triggers
        }, status=status.HTTP_200_OK)
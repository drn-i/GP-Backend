from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from firebase_admin import messaging
from apps.profiles.models import MedicalProfile
from utils.mongo_client import get_mongo_db
from datetime import datetime, timedelta, timezone
from collections import Counter
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
    Returns recent Segment 1 aligned results first, falling back to legacy risk_results.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if request.user.username != user_id and not request.user.is_staff:
            return Response({"error": "Unauthorized data access"}, status=status.HTTP_403_FORBIDDEN)

        try:
            limit = int(request.query_params.get('limit', 1))
        except ValueError:
            limit = 1

        db = get_mongo_db()

        # Prefer Segment 1 aligned results
        cursor = db.segment1_results.find(
            {"user_id": user_id},
            sort=[("server_received_at", -1)]
        ).limit(limit)

        results = list(cursor)

        # Fallback to legacy collection if no Segment 1 results exist
        if not results:
            cursor = db.risk_results.find(
                {"user_id": user_id},
                sort=[("server_received_at", -1)]
            ).limit(limit)
            results = list(cursor)

        for res in results:
            res["_id"] = str(res["_id"])

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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payload = request.data
        records = payload if isinstance(payload, list) else [payload]

        serializer = Segment1ResultSerializer(data=records, many=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        valid_records = serializer.validated_data
        db = get_mongo_db()

        processed = 0

        for record in valid_records:
            if request.user.username != record["user_id"] and not request.user.is_staff:
                return Response({"error": "Unauthorized data submission"}, status=status.HTTP_403_FORBIDDEN)

            record["server_received_at"] = datetime.now(timezone.utc)

            filter_query = {
                "user_id": record["user_id"],
                "window.start_emotibit_ms": record["window"]["start_emotibit_ms"],
            }

            db.segment1_results.update_one(
                filter_query,
                {"$set": record},
                upsert=True
            )
            processed += 1

        return Response({
            "status": "success",
            "records_processed": processed
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
    GET /api/summary/{user_id}/
    Returns the latest 10 Segment 1 aligned results first, falling back to legacy risk_results.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if request.user.username != user_id and not request.user.is_staff:
            return Response({"error": "Unauthorized data access"}, status=status.HTTP_403_FORBIDDEN)

        db = get_mongo_db()

        cursor = db.segment1_results.find(
            {"user_id": user_id},
            sort=[("server_received_at", -1)]
        ).limit(10)

        results = list(cursor)

        if not results:
            cursor = db.risk_results.find(
                {"user_id": user_id},
                sort=[("server_received_at", -1)]
            ).limit(10)
            results = list(cursor)

        if not results:
            return Response({"message": "No risk history found"}, status=status.HTTP_404_NOT_FOUND)

        for res in results:
            res["_id"] = str(res["_id"])

        return Response(results, status=status.HTTP_200_OK)
    
class AllRiskEventsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        db = get_mongo_db()

        results = list(
            db.segment1_results.find({}, sort=[("server_received_at", -1)]).limit(50)
        )

        if not results:
            results = list(
                db.risk_results.find({}, sort=[("server_received_at", -1)]).limit(50)
            )

        for res in results:
            res["_id"] = str(res["_id"])

        return Response(results, status=status.HTTP_200_OK)

class MobileDashboardView(APIView):
    """
    GET /api/dashboard/{user_id}/
    Returns dashboard data from Segment 1 aligned results first, falling back to legacy risk_results.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if request.user.username != user_id and not request.user.is_staff:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        db = get_mongo_db()

        latest_result = db.segment1_results.find_one(
            {"user_id": user_id},
            sort=[("server_received_at", -1)]
        )

        if latest_result:
            llm_result = latest_result.get("llm_result", {})
            stress_detected = llm_result.get("stress_detected", False)

            dashboard_data = {
                "risk_rate": "High" if stress_detected else "Low",
                "stress_level": "High" if stress_detected else "Low",
                "average_hr": 0,
                "daily_summary": llm_result.get("summary", "No AI summary available yet."),
                "last_updated": latest_result.get("timestamp")
            }
            return Response(dashboard_data, status=status.HTTP_200_OK)

        # Fallback to legacy risk_results
        latest_legacy = db.risk_results.find_one(
            {"user_id": user_id},
            sort=[("server_received_at", -1)]
        )

        if not latest_legacy:
            return Response({
                "risk_rate": "N/A",
                "stress_level": "No Data",
                "average_hr": 0,
                "daily_summary": "Please wear your device to start collecting data."
            }, status=status.HTTP_200_OK)

        recent_cursor = db.risk_results.find(
            {"user_id": user_id},
            sort=[("server_received_at", -1)]
        ).limit(10)
        recent_results = list(recent_cursor)

        total_hr = sum(res.get("features", {}).get("hr_mean", 0) for res in recent_results)
        avg_hr = round(total_hr / len(recent_results)) if recent_results else 0

        dashboard_data = {
            "risk_rate": latest_legacy.get("risk_level", "Unknown"),
            "stress_level": latest_legacy.get("risk_level", "Unknown"),
            "average_hr": avg_hr,
            "daily_summary": latest_legacy.get("summary", "No AI summary available yet."),
            "last_updated": latest_legacy.get("timestamp")
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
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if request.user.username != user_id and not request.user.is_staff:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        date_str = request.query_params.get("date")
        if date_str:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            target_date = datetime.now(timezone.utc).date()

        start_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = start_dt + timedelta(days=1)

        db = get_mongo_db()

        results = list(db.segment1_results.find({
            "user_id": user_id,
            "server_received_at": {"$gte": start_dt, "$lt": end_dt}
        }))

        if not results:
            return Response({
                "date": target_date.isoformat(),
                "avg_hr": 0,
                "stress_level": "No Data",
                "activity_level": "No Data",
                "summary": "No Segment 1 results recorded for this date."
            }, status=status.HTTP_200_OK)

        labels = [
            "High" if r.get("llm_result", {}).get("stress_detected") else "Low"
            for r in results
        ]
        dominant = Counter(labels).most_common(1)[0][0]

        return Response({
            "date": target_date.isoformat(),
            "avg_hr": 0,
            "stress_level": dominant,
            "activity_level": "Normal",
            "summary": f"Segment 1 results for this date were predominantly {dominant} stress."
        }, status=status.HTTP_200_OK)


# -------------------------------------------------------------------
#  WEEKLY TRENDS API (Charts & Graphs)
# -------------------------------------------------------------------
class WeeklyAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if request.user.username != user_id and not request.user.is_staff:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        db = get_mongo_db()
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)

        results = list(db.segment1_results.find({
            "user_id": user_id,
            "server_received_at": {"$gte": seven_days_ago}
        }))

        weekdays = {"Mon": 0, "Tue": 0, "Wed": 0, "Thu": 0, "Fri": 0, "Sat": 0, "Sun": 0}
        pie = {"Stress": 0, "Not Stress": 0}

        for r in results:
            ts = r.get("server_received_at")
            if ts:
                weekdays[ts.strftime("%a")] += 1

            if r.get("llm_result", {}).get("stress_detected"):
                pie["Stress"] += 1
            else:
                pie["Not Stress"] += 1

        return Response({
            "bar_chart_data": weekdays,
            "pie_chart_data": pie
        }, status=status.HTTP_200_OK)
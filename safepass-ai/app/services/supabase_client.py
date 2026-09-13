"""
SafePass AI — Supabase Cloud Database Client
Provides cloud storage for:
1. Driver Trip & Route Corridor History ('trips')
2. Citizen Crowdsourced Hazard Reports ('hazard_reports')
3. Emergency SOS Incident Logs ('emergency_sos_logs')

Supports both live Supabase cloud connection and local resilient fallback.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("safepass.supabase")

# In-memory local stores for offline/demo operation when Supabase keys are pending
_LOCAL_TRIPS: List[Dict[str, Any]] = []
_LOCAL_HAZARDS: List[Dict[str, Any]] = []
_LOCAL_SOS_LOGS: List[Dict[str, Any]] = []

class SafePassSupabaseClient:
    def __init__(self):
        self.url = (os.getenv("SUPABASE_URL") or "").strip()
        self.key = (os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY") or "").strip()
        self.client = None
        self._connected = False

        if self.url and self.key and not self.url.startswith("https://your-project"):
            try:
                from supabase import create_client
                self.client = create_client(self.url, self.key)
                self._connected = True
                logger.info(f"Connected to Supabase project at {self.url}")
            except Exception as e:
                logger.warning(f"Failed to initialize Supabase client: {e}. Running in local resilient mode.")
                self._connected = False
        else:
            logger.info("No active SUPABASE_URL configured. Running with resilient local cloud store.")

    @property
    def is_connected(self) -> bool:
        return self._connected and self.client is not None

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self.is_connected,
            "project_url": self.url if self.is_connected else None,
            "mode": "supabase_cloud" if self.is_connected else "local_resilient_store",
            "trips_count": len(_LOCAL_TRIPS),
            "hazards_count": len(_LOCAL_HAZARDS),
            "sos_count": len(_LOCAL_SOS_LOGS),
        }

    # ── 1. Trip & Corridor History ───────────────────────────────────────────

    async def save_trip(self, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save a computed corridor route to Supabase or local store."""
        record = {
            "created_at": datetime.utcnow().isoformat(),
            "origin_name": trip_data.get("origin_name", "Unknown Origin"),
            "origin_lat": float(trip_data.get("origin_lat", 0.0)),
            "origin_lng": float(trip_data.get("origin_lng", 0.0)),
            "dest_name": trip_data.get("dest_name", "Unknown Destination"),
            "dest_lat": float(trip_data.get("dest_lat", 0.0)),
            "dest_lng": float(trip_data.get("dest_lng", 0.0)),
            "corridor_name": trip_data.get("corridor_name", "SafePass Route"),
            "safety_score": float(trip_data.get("safety_score", 0.0)),
            "avg_cri": float(trip_data.get("avg_cri", 0.0)),
            "distance_km": float(trip_data.get("distance_km", 0.0)),
            "est_time_min": int(trip_data.get("est_time_min", 0)),
            "danger_zones": int(trip_data.get("danger_zones", 0)),
            "weather": trip_data.get("weather", {}),
            "user_id": trip_data.get("user_id", "driver_anon"),
        }

        if self.is_connected:
            try:
                res = self.client.table("trips").insert(record).execute()
                return {
                    "success": True,
                    "storage": "supabase",
                    "data": res.data[0] if res.data else record,
                    "message": "Trip successfully logged to Supabase cloud database!"
                }
            except Exception as e:
                logger.error(f"Supabase trips insert error: {e}")
                # Fall through to local store

        _LOCAL_TRIPS.insert(0, record)
        return {
            "success": True,
            "storage": "local_store",
            "data": record,
            "message": "Trip saved to local session store (Supabase credentials pending)."
        }

    async def get_recent_trips(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Retrieve recent saved trips."""
        if self.is_connected:
            try:
                res = self.client.table("trips").select("*").order("created_at", desc=True).limit(limit).execute()
                if res.data:
                    return res.data
            except Exception as e:
                logger.error(f"Supabase trips fetch error: {e}")

        return _LOCAL_TRIPS[:limit]

    # ── 2. Crowdsourced Hazard Reports ───────────────────────────────────────

    async def report_hazard(self, hazard_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a citizen or driver hazard report along an Indian highway."""
        record = {
            "created_at": datetime.utcnow().isoformat(),
            "title": hazard_data.get("title") or "Reported Highway Hazard",
            "hazard_type": hazard_data.get("hazard_type", "blackspot"),
            "severity": float(hazard_data.get("severity", 5.0)),
            "lat": float(hazard_data.get("lat", 0.0)),
            "lng": float(hazard_data.get("lng", 0.0)),
            "highway": hazard_data.get("highway", "National Highway"),
            "description": hazard_data.get("description", "Reported by motorist via SafePass AI"),
            "reported_by": hazard_data.get("reported_by", "Citizen Reporter"),
            "verified": False,
        }

        if self.is_connected:
            try:
                res = self.client.table("hazard_reports").insert(record).execute()
                return {
                    "success": True,
                    "storage": "supabase",
                    "data": res.data[0] if res.data else record,
                    "message": "Hazard alert published to Supabase community network!"
                }
            except Exception as e:
                logger.error(f"Supabase hazard insert error: {e}")

        _LOCAL_HAZARDS.insert(0, record)
        return {
            "success": True,
            "storage": "local_store",
            "data": record,
            "message": "Hazard registered in local session network."
        }

    async def get_community_hazards(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent community hazard reports."""
        if self.is_connected:
            try:
                res = self.client.table("hazard_reports").select("*").order("created_at", desc=True).limit(limit).execute()
                if res.data:
                    return res.data
            except Exception as e:
                logger.error(f"Supabase hazards fetch error: {e}")

        return _LOCAL_HAZARDS[:limit]

    # ── 3. Emergency SOS Incident Logs ────────────────────────────────────────

    async def log_sos_incident(self, sos_data: Dict[str, Any]) -> Dict[str, Any]:
        """Log emergency 112 / 1033 / 108 dial with live GPS telemetry."""
        record = {
            "created_at": datetime.utcnow().isoformat(),
            "user_lat": float(sos_data.get("lat", 0.0)),
            "user_lng": float(sos_data.get("lng", 0.0)),
            "service_dialed": sos_data.get("service", "112"),
            "status": "DISPATCH_ALERT_TRIGGERED",
            "notes": sos_data.get("notes", "SOS triggered from SafePass Maps"),
        }

        if self.is_connected:
            try:
                res = self.client.table("emergency_sos_logs").insert(record).execute()
                return {
                    "success": True,
                    "storage": "supabase",
                    "data": res.data[0] if res.data else record,
                    "message": "Emergency dispatch logged to Supabase incident database."
                }
            except Exception as e:
                logger.error(f"Supabase SOS insert error: {e}")

        _LOCAL_SOS_LOGS.insert(0, record)
        return {
            "success": True,
            "storage": "local_store",
            "data": record,
            "message": "SOS emergency telemetry registered locally."
        }

# Global singleton
supabase_service = SafePassSupabaseClient()

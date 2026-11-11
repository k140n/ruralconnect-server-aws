"""
Live Courier Tracking Service for RuralConnect.

Supports:
1. Real Shiprocket API integration (Production & Sandbox accounts).
2. Intelligent Simulated Sandbox mode for local testing without requiring active paid API keys.
3. Fallback direct web tracking links for major Indian couriers (Delhivery, India Post, Blue Dart, DTDC).
"""

import logging
import os
import requests
from datetime import timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

SHIPROCKET_AUTH_URL = "https://apiv2.shiprocket.in/v2/auth/login"
SHIPROCKET_TRACK_URL = "https://apiv2.shiprocket.in/v2/courier/track/awb/{awb}"


def get_shiprocket_token():
    """
    Retrieves or caches a Shiprocket Bearer JWT token.
    Token validity is typically 10 days; we cache for 24 hours.
    """
    cache_key = "shiprocket_auth_jwt_token"
    token = cache.get(cache_key)
    if token:
        return token

    email = getattr(settings, 'SHIPROCKET_EMAIL', '') or os.getenv('SHIPROCKET_EMAIL', '')
    password = getattr(settings, 'SHIPROCKET_PASSWORD', '') or os.getenv('SHIPROCKET_PASSWORD', '')

    if not email or not password:
        return None

    try:
        resp = requests.post(
            SHIPROCKET_AUTH_URL,
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=8
        )
        if resp.status_code == 200:
            data = resp.json()
            token = data.get('token')
            if token:
                cache.set(cache_key, token, timeout=86400)  # 24 hours
                return token
        else:
            logger.warning(f"Shiprocket auth failed: HTTP {resp.status_code} - {resp.text}")
    except Exception as exc:
        logger.error(f"Error authenticating with Shiprocket: {exc}")

    return None


def get_direct_courier_url(courier_name, tracking_number):
    """
    Returns the official external tracking web URL for direct customer tracking.
    """
    if not tracking_number:
        return ""

    courier = (courier_name or '').lower().strip()
    t = str(tracking_number).strip()

    if 'delhivery' in courier:
        return f"https://www.delhivery.com/track/package/{t}"
    elif 'india post' in courier or 'indiapost' in courier or 'speed post' in courier:
        return "https://www.indiapost.gov.in/_layouts/15/dop.portal.tracking/trackconsignment.aspx"
    elif 'bluedart' in courier or 'blue dart' in courier:
        return f"https://www.bluedart.com/tracking?track={t}"
    elif 'dtdc' in courier:
        return f"https://www.dtdc.in/tracking/shipment-tracking.asp?trNo={t}"
    elif 'shadowfax' in courier:
        return f"https://tracker.shadowfax.in/#/track?awb={t}"
    elif 'shiprocket' in courier:
        return f"https://shiprocket.co/tracking/{t}"

    # Default fallback
    return f"https://t.17track.net/en#nums={t}"


def get_mock_tracking_data(order_item):
    """
    Generates realistic, dynamic live tracking data for sandbox testing.
    Adapts based on OrderItem status and tracking number keywords.
    """
    now = timezone.now()
    created = order_item.created_at or (now - timedelta(days=2))
    origin = order_item.seller.location or "Thrissur, Kerala"
    destination = f"{order_item.order.city}, {order_item.order.state}" if order_item.order.city else "Customer Address"
    
    courier = order_item.courier_name or "Shiprocket Express (Delhivery)"
    awb = order_item.tracking_number or f"SR{order_item.id:06d}IN"

    # Determine simulated status
    code = (order_item.tracking_number or '').upper()
    status = order_item.status

    if 'DELIVERED' in code or status == 'delivered':
        step = 4
        current_status = "Delivered"
        status_code = "DELIVERED"
        eta = (created + timedelta(days=2)).strftime("%d %b %Y")
    elif 'OUT' in code:
        step = 3
        current_status = "Out for Delivery"
        status_code = "OUT_FOR_DELIVERY"
        eta = "Today by 7:00 PM"
    elif 'TRANSIT' in code or status == 'shipped':
        step = 2
        current_status = "In Transit"
        status_code = "IN_TRANSIT"
        eta = (now + timedelta(days=2)).strftime("%d %b %Y")
    elif status == 'confirmed':
        step = 1
        current_status = "Ready for Pickup"
        status_code = "READY_FOR_PICKUP"
        eta = (now + timedelta(days=3)).strftime("%d %b %Y")
    else:
        step = 0
        current_status = "Order Placed with Artisan"
        status_code = "PENDING"
        eta = (now + timedelta(days=4)).strftime("%d %b %Y")

    # Build timeline activities
    scans = []
    
    # Checkpoint 1: Order confirmed
    scans.append({
        "status": "Order Confirmed",
        "activity": f"Artisan {order_item.seller.business_name} acknowledged handcrafted item.",
        "location": origin,
        "timestamp": created.strftime("%d %b %Y, %I:%M %p"),
        "done": step >= 1
    })

    # Checkpoint 2: Picked up by courier
    pickup_time = created + timedelta(hours=8)
    scans.append({
        "status": "Package Handed Over",
        "activity": f"Courier agent picked up package from workshop in {origin}.",
        "location": origin,
        "timestamp": pickup_time.strftime("%d %b %Y, %I:%M %p"),
        "done": step >= 2
    })

    # Checkpoint 3: In Transit / Hub
    transit_time = pickup_time + timedelta(hours=14)
    scans.append({
        "status": "In Transit at Regional Hub",
        "activity": "Consignment sorted at regional automated transshipment hub.",
        "location": f"Regional Logistics Hub ({order_item.seller.origin_region()})",
        "timestamp": transit_time.strftime("%d %b %Y, %I:%M %p"),
        "done": step >= 2
    })

    # Checkpoint 4: Out for Delivery
    out_time = now - timedelta(hours=2) if step >= 3 else (transit_time + timedelta(days=1))
    scans.append({
        "status": "Out for Delivery",
        "activity": f"Shipment is out with courier delivery executive for {destination}.",
        "location": destination,
        "timestamp": out_time.strftime("%d %b %Y, %I:%M %p"),
        "done": step >= 3
    })

    # Checkpoint 5: Delivered
    deliv_time = now - timedelta(minutes=45) if step >= 4 else (out_time + timedelta(hours=4))
    scans.append({
        "status": "Delivered",
        "activity": f"Package safely delivered to recipient {order_item.order.full_name}.",
        "location": destination,
        "timestamp": deliv_time.strftime("%d %b %Y, %I:%M %p"),
        "done": step >= 4
    })

    # Filter to only show relevant and current scans
    visible_scans = [s for s in scans if s["done"]]
    if not visible_scans:
        visible_scans = [scans[0]]

    # Step progress percentage: 0 -> 15%, 1 -> 35%, 2 -> 65%, 3 -> 85%, 4 -> 100%
    progress_map = {0: 15, 1: 35, 2: 65, 3: 85, 4: 100}

    return {
        "success": True,
        "is_sandbox": True,
        "order_number": order_item.order.order_number,
        "product_name": order_item.product_name,
        "courier_name": courier,
        "tracking_number": awb,
        "current_status": current_status,
        "status_code": status_code,
        "progress_percent": progress_map.get(step, 20),
        "current_step": step,
        "origin": origin,
        "destination": destination,
        "expected_delivery": eta,
        "direct_tracking_url": get_direct_courier_url(courier, awb),
        "activities": visible_scans[::-1],  # Newest first
    }


def track_shipment(order_item):
    """
    Main entrypoint: Attempts real Shiprocket API call if credentials exist.
    Seamlessly falls back to Sandbox simulator if credentials are missing or test AWB is detected.
    """
    awb = (order_item.tracking_number or '').strip()

    # If AWB indicates a test or credentials not set, use high-fidelity sandbox
    token = get_shiprocket_token()
    if not token or not awb or awb.upper().startswith('TEST') or getattr(settings, 'SHIPROCKET_SANDBOX', True) and not token:
        return get_mock_tracking_data(order_item)

    # Attempt live Shiprocket tracking
    try:
        url = SHIPROCKET_TRACK_URL.format(awb=awb)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            track_data = data.get('tracking_data', {})
            
            if track_data.get('track_status') == 1:
                ship_track = (track_data.get('shipment_track') or [{}])[0]
                activities_raw = track_data.get('shipment_track_activities') or []

                scans = []
                for act in activities_raw:
                    scans.append({
                        "status": act.get('status') or act.get('activity', 'In Transit'),
                        "activity": act.get('activity', ''),
                        "location": act.get('location', ''),
                        "timestamp": act.get('date', ''),
                        "done": True
                    })

                current_status = ship_track.get('current_status', 'In Transit')
                eta = ship_track.get('expected_date') or "Within 2-4 business days"

                # Calculate progress
                status_lower = current_status.lower()
                step = 2
                progress = 60
                if 'delivered' in status_lower:
                    step = 4
                    progress = 100
                elif 'out for delivery' in status_lower:
                    step = 3
                    progress = 85
                elif 'pickup' in status_lower or 'manifest' in status_lower:
                    step = 1
                    progress = 35

                return {
                    "success": True,
                    "is_sandbox": False,
                    "order_number": order_item.order.order_number,
                    "product_name": order_item.product_name,
                    "courier_name": ship_track.get('courier_name') or order_item.courier_name or 'Shiprocket',
                    "tracking_number": awb,
                    "current_status": current_status,
                    "status_code": current_status.upper(),
                    "progress_percent": progress,
                    "current_step": step,
                    "origin": ship_track.get('origin', ''),
                    "destination": ship_track.get('destination', ''),
                    "expected_delivery": eta,
                    "direct_tracking_url": get_direct_courier_url(order_item.courier_name, awb),
                    "activities": scans,
                }
    except Exception as exc:
        logger.error(f"Shiprocket API exception for AWB {awb}: {exc}")

    # Fallback to sandbox if API call fails or is unconfigured
    return get_mock_tracking_data(order_item)


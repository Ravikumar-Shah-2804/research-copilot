"""
Security monitoring and alerting system with intrusion detection and threat intelligence
"""
import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import re
import ipaddress
import geoip2.database
import socket
import struct

from ..config import settings
from ..utils.security_logging import security_logger, audit_logger
from ..services.cache import RedisCache
from .audit import audit_service

logger = logging.getLogger(__name__)


class SecurityEvent:
    """Security event data structure"""

    def __init__(
        self,
        event_type: str,
        severity: str,
        source_ip: str,
        user_id: Optional[str] = None,
        details: Dict[str, Any] = None,
        timestamp: Optional[datetime] = None
    ):
        self.event_type = event_type
        self.severity = severity
        self.source_ip = source_ip
        self.user_id = user_id
        self.details = details or {}
        self.timestamp = timestamp or datetime.utcnow()
        self.id = f"{event_type}_{int(time.time() * 1000)}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            "id": self.id,
            "event_type": self.event_type,
            "severity": self.severity,
            "source_ip": self.source_ip,
            "user_id": self.user_id,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class IntrusionDetectionSystem:
    """Intrusion Detection System with pattern matching and anomaly detection"""

    def __init__(self):
        self.cache = RedisCache()
        self.suspicious_patterns = self._load_suspicious_patterns()
        self.rate_limits = defaultdict(lambda: deque(maxlen=100))
        self.blocked_ips: Set[str] = set()
        self.geoip_db = self._load_geoip_database()

        # Thresholds for anomaly detection
        self.thresholds = {
            "failed_login_attempts": 5,
            "requests_per_minute": 100,
            "suspicious_patterns": 3,
            "unusual_locations": 2
        }

    def _load_suspicious_patterns(self) -> List[Dict[str, Any]]:
        """Load patterns for intrusion detection"""
        return [
            {
                "name": "sql_injection",
                "pattern": re.compile(r"(union\s+select|;\s*drop|script\s*alert)", re.IGNORECASE),
                "severity": "high",
                "category": "injection"
            },
            {
                "name": "xss_attempt",
                "pattern": re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE),
                "severity": "high",
                "category": "xss"
            },
            {
                "name": "path_traversal",
                "pattern": re.compile(r"\.\./|\.\.\\", re.IGNORECASE),
                "severity": "high",
                "category": "traversal"
            },
            {
                "name": "command_injection",
                "pattern": re.compile(r"[;&|]\s*(?:cat|ls|pwd|whoami|netstat)", re.IGNORECASE),
                "severity": "critical",
                "category": "injection"
            },
            {
                "name": "directory_listing",
                "pattern": re.compile(r"/\w+/\w+/\w+/\w+/\w+/\w+/", re.IGNORECASE),
                "severity": "medium",
                "category": "reconnaissance"
            }
        ]

    def _load_geoip_database(self):
        """Load GeoIP database for location analysis"""
        try:
            # This would typically load a MaxMind GeoIP database
            # For now, return None and implement basic checks
            return None
        except Exception:
            logger.warning("GeoIP database not available")
            return None

    async def analyze_request(self, request_data: Dict[str, Any]) -> List[SecurityEvent]:
        """Analyze a request for security threats"""
        events = []

        ip = request_data.get("ip_address", "")
        user_id = request_data.get("user_id")
        user_agent = request_data.get("user_agent", "")
        url = request_data.get("url", "")
        method = request_data.get("method", "")
        body = request_data.get("body", "")

        # Check for blocked IPs
        if ip in self.blocked_ips:
            events.append(SecurityEvent(
                "blocked_ip_access",
                "critical",
                ip,
                user_id,
                {"reason": "IP is in blocklist"}
            ))
            return events

        # Pattern matching
        pattern_events = await self._check_patterns(ip, user_id, url, body, user_agent)
        events.extend(pattern_events)

        # Rate limiting analysis
        rate_events = await self._check_rate_limits(ip, user_id)
        events.extend(rate_events)

        # Behavioral analysis
        behavior_events = await self._check_behavioral_anomalies(ip, user_id, request_data)
        events.extend(behavior_events)

        # Location analysis
        location_events = await self._check_location_anomalies(ip, user_id)
        events.extend(location_events)

        return events

    async def _check_patterns(
        self, ip: str, user_id: str, url: str, body: str, user_agent: str
    ) -> List[SecurityEvent]:
        """Check for suspicious patterns in request data"""
        events = []
        check_data = f"{url} {body} {user_agent}"

        for pattern_info in self.suspicious_patterns:
            pattern = pattern_info["pattern"]
            if pattern.search(check_data):
                events.append(SecurityEvent(
                    "suspicious_pattern_detected",
                    pattern_info["severity"],
                    ip,
                    user_id,
                    {
                        "pattern_name": pattern_info["name"],
                        "category": pattern_info["category"],
                        "matched_data": pattern_info["pattern"].findall(check_data)[:3]  # Limit matches
                    }
                ))

        return events

    async def _check_rate_limits(self, ip: str, user_id: str) -> List[SecurityEvent]:
        """Check for rate limiting violations"""
        events = []
        current_time = time.time()

        # Track requests per IP
        ip_key = f"rate_ip_{ip}"
        ip_requests = await self.cache.get(ip_key) or []
        ip_requests.append(current_time)

        # Keep only requests from last minute
        ip_requests = [t for t in ip_requests if current_time - t < 60]
        await self.cache.set(ip_key, ip_requests, ttl=60)

        if len(ip_requests) > self.thresholds["requests_per_minute"]:
            events.append(SecurityEvent(
                "rate_limit_exceeded",
                "medium",
                ip,
                user_id,
                {
                    "request_count": len(ip_requests),
                    "threshold": self.thresholds["requests_per_minute"],
                    "time_window": "60 seconds"
                }
            ))

        # Track failed login attempts per user
        if user_id:
            login_key = f"failed_logins_{user_id}"
            failed_attempts = await self.cache.get(login_key) or []
            failed_attempts.append(current_time)

            # Keep only attempts from last hour
            failed_attempts = [t for t in failed_attempts if current_time - t < 3600]
            await self.cache.set(login_key, failed_attempts, ttl=3600)

            if len(failed_attempts) > self.thresholds["failed_login_attempts"]:
                events.append(SecurityEvent(
                    "brute_force_attempt",
                    "high",
                    ip,
                    user_id,
                    {
                        "failed_attempts": len(failed_attempts),
                        "threshold": self.thresholds["failed_login_attempts"],
                        "time_window": "1 hour"
                    }
                ))

        return events

    async def _check_behavioral_anomalies(
        self, ip: str, user_id: str, request_data: Dict[str, Any]
    ) -> List[SecurityEvent]:
        """Check for behavioral anomalies"""
        events = []

        # Check for unusual user agents
        user_agent = request_data.get("user_agent", "")
        if self._is_suspicious_user_agent(user_agent):
            events.append(SecurityEvent(
                "suspicious_user_agent",
                "medium",
                ip,
                user_id,
                {"user_agent": user_agent}
            ))

        # Check for unusual request patterns
        url = request_data.get("url", "")
        if self._is_suspicious_url_pattern(url):
            events.append(SecurityEvent(
                "suspicious_url_pattern",
                "medium",
                ip,
                user_id,
                {"url": url}
            ))

        return events

    async def _check_location_anomalies(self, ip: str, user_id: str) -> List[SecurityEvent]:
        """Check for location-based anomalies"""
        events = []

        if not user_id or not self.geoip_db:
            return events

        try:
            # Get user's typical locations
            location_key = f"user_locations_{user_id}"
            typical_locations = await self.cache.get(location_key) or []

            # Get current location
            current_location = self._get_location_from_ip(ip)

            if current_location:
                # Check if location is unusual
                unusual = True
                for typical in typical_locations:
                    if self._locations_similar(current_location, typical):
                        unusual = False
                        break

                if unusual and len(typical_locations) > 0:
                    events.append(SecurityEvent(
                        "unusual_location",
                        "medium",
                        ip,
                        user_id,
                        {
                            "current_location": current_location,
                            "typical_locations": typical_locations
                        }
                    ))

                # Update typical locations
                if current_location not in typical_locations:
                    typical_locations.append(current_location)
                    if len(typical_locations) > 5:  # Keep only 5 recent locations
                        typical_locations.pop(0)
                    await self.cache.set(location_key, typical_locations, ttl=86400 * 30)  # 30 days

        except Exception as e:
            logger.error(f"Location analysis error: {e}")

        return events

    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is suspicious"""
        suspicious_patterns = [
            r"python-requests/\d+",  # Automated tools
            r"curl/\d+",
            r"wget/\d+",
            r"sqlmap",  # SQL injection tools
            r"nikto",  # Web server scanner
            r"dirbuster",  # Directory busting tool
            r"nessus",  # Vulnerability scanner
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, user_agent, re.IGNORECASE):
                return True

        return False

    def _is_suspicious_url_pattern(self, url: str) -> bool:
        """Check if URL pattern is suspicious"""
        suspicious_patterns = [
            r"\.\./",  # Directory traversal
            r"%2e%2e%2f",  # URL encoded traversal
            r"adminer\.php",
            r"phpmyadmin",
            r"webdav",
            r"\.env$",
            r"wp-admin",
            r"administrator",
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True

        return False

    def _get_location_from_ip(self, ip: str) -> Optional[Dict[str, Any]]:
        """Get location information from IP address"""
        try:
            # This would use the GeoIP database
            # For now, return basic info
            return {
                "country": "Unknown",
                "city": "Unknown",
                "coordinates": [0.0, 0.0]
            }
        except Exception:
            return None

    def _locations_similar(self, loc1: Dict[str, Any], loc2: Dict[str, Any]) -> bool:
        """Check if two locations are similar"""
        # Simple distance check (would need proper geolocation calculation)
        return loc1.get("country") == loc2.get("country")

    def block_ip(self, ip: str, reason: str, duration: int = 3600):
        """Block an IP address temporarily"""
        self.blocked_ips.add(ip)

        # Schedule unblock
        async def unblock():
            await asyncio.sleep(duration)
            self.blocked_ips.discard(ip)
            logger.info(f"IP {ip} unblocked after {duration} seconds")

        asyncio.create_task(unblock())

        logger.warning(f"IP {ip} blocked for {duration} seconds: {reason}")

    def unblock_ip(self, ip: str):
        """Unblock an IP address"""
        self.blocked_ips.discard(ip)
        logger.info(f"IP {ip} manually unblocked")


class SecurityAlertManager:
    """Security alert management and notification system"""

    def __init__(self):
        self.cache = RedisCache()
        self.alert_thresholds = {
            "critical": 1,  # Alert immediately
            "high": 5,      # Alert after 5 events
            "medium": 10,   # Alert after 10 events
            "low": 50       # Alert after 50 events
        }
        self.alert_cooldown = 300  # 5 minutes between similar alerts

    async def process_security_events(self, events: List[SecurityEvent]):
        """Process security events and generate alerts"""
        for event in events:
            await self._process_event(event)

    async def _process_event(self, event: SecurityEvent):
        """Process individual security event"""
        # Log the event
        await security_logger.log_security_event(
            event.event_type,
            f"Security event: {event.event_type}",
            user_id=event.user_id,
            ip_address=event.source_ip,
            metadata=event.details,
            severity=event.severity
        )

        # Check if we should generate an alert
        should_alert = await self._should_generate_alert(event)

        if should_alert:
            await self._generate_alert(event)

        # Update event counters
        await self._update_event_counters(event)

    async def _should_generate_alert(self, event: SecurityEvent) -> bool:
        """Determine if an alert should be generated"""
        threshold = self.alert_thresholds.get(event.severity, 50)

        # Check event frequency
        event_key = f"event_count_{event.event_type}_{event.source_ip}"
        count = await self.cache.get(event_key) or 0
        count += 1
        await self.cache.set(event_key, count, ttl=3600)  # 1 hour window

        return count >= threshold

    async def _generate_alert(self, event: SecurityEvent):
        """Generate a security alert"""
        alert_data = {
            "alert_id": f"alert_{int(time.time() * 1000)}",
            "event_type": event.event_type,
            "severity": event.severity,
            "source_ip": event.source_ip,
            "user_id": event.user_id,
            "details": event.details,
            "timestamp": event.timestamp.isoformat(),
            "recommendations": self._get_recommendations(event)
        }

        # Log alert
        logger.critical(f"SECURITY ALERT: {event.event_type} from {event.source_ip}", extra=alert_data)

        # Send notifications (would integrate with email, Slack, etc.)
        await self._send_notifications(alert_data)

        # Take automated actions if configured
        await self._take_automated_actions(event)

    def _get_recommendations(self, event: SecurityEvent) -> List[str]:
        """Get recommendations based on event type"""
        recommendations = {
            "brute_force_attempt": [
                "Implement account lockout after failed attempts",
                "Enable two-factor authentication",
                "Monitor for further suspicious activity"
            ],
            "suspicious_pattern_detected": [
                "Review input validation rules",
                "Implement Web Application Firewall (WAF)",
                "Monitor for similar patterns"
            ],
            "rate_limit_exceeded": [
                "Review rate limiting configuration",
                "Implement progressive delays",
                "Consider IP-based blocking"
            ],
            "unusual_location": [
                "Verify user identity",
                "Enable location-based authentication",
                "Review access patterns"
            ]
        }

        return recommendations.get(event.event_type, ["Review security logs", "Investigate the incident"])

    async def _send_notifications(self, alert_data: Dict[str, Any]):
        """Send alert notifications"""
        # This would integrate with various notification systems
        # For now, just log the alert
        logger.critical("Security Alert Generated", extra=alert_data)

    async def _take_automated_actions(self, event: SecurityEvent):
        """Take automated actions based on event severity"""
        if event.severity == "critical":
            # For critical events, consider blocking the IP
            if event.event_type in ["brute_force_attempt", "suspicious_pattern_detected"]:
                # This would need access to the IDS instance
                logger.warning(f"Automated action recommended for {event.event_type}")

    async def _update_event_counters(self, event: SecurityEvent):
        """Update security event counters for monitoring"""
        counters_key = "security_event_counters"
        counters = await self.cache.get(counters_key) or {}

        event_key = f"{event.severity}_{event.event_type}"
        counters[event_key] = counters.get(event_key, 0) + 1

        await self.cache.set(counters_key, counters, ttl=86400)  # 24 hours

    async def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        counters = await self.cache.get("security_event_counters") or {}

        return {
            "total_events": sum(counters.values()),
            "events_by_type": counters,
            "blocked_ips": list(self.blocked_ips) if hasattr(self, 'blocked_ips') else [],
            "timestamp": datetime.utcnow().isoformat()
        }


class ThreatIntelligence:
    """Threat intelligence integration"""

    def __init__(self):
        self.cache = RedisCache()
        self.threat_feeds = [
            "https://api.abuseipdb.com/api/v2/check",
            # Add more threat intelligence feeds
        ]
        self.local_threat_db: Set[str] = set()

    async def check_ip_threat_level(self, ip: str) -> Dict[str, Any]:
        """Check threat level of an IP address"""
        # Check local threat database first
        if ip in self.local_threat_db:
            return {
                "threat_level": "high",
                "source": "local_db",
                "confidence": 1.0
            }

        # Check cache
        cache_key = f"threat_ip_{ip}"
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return cached_result

        # Query threat intelligence feeds
        threat_info = await self._query_threat_feeds(ip)

        # Cache result for 1 hour
        await self.cache.set(cache_key, threat_info, ttl=3600)

        return threat_info

    async def _query_threat_feeds(self, ip: str) -> Dict[str, Any]:
        """Query external threat intelligence feeds"""
        # This would implement actual API calls to threat intelligence services
        # For now, return a basic response
        return {
            "threat_level": "unknown",
            "source": "external_feeds",
            "confidence": 0.0,
            "last_checked": datetime.utcnow().isoformat()
        }

    def add_to_threat_db(self, ip: str, reason: str):
        """Add IP to local threat database"""
        self.local_threat_db.add(ip)
        logger.warning(f"IP {ip} added to threat database: {reason}")

    def remove_from_threat_db(self, ip: str):
        """Remove IP from local threat database"""
        self.local_threat_db.discard(ip)
        logger.info(f"IP {ip} removed from threat database")


# Global instances
ids = IntrusionDetectionSystem()
alert_manager = SecurityAlertManager()
threat_intelligence = ThreatIntelligence()


async def analyze_security_event(request_data: Dict[str, Any]) -> List[SecurityEvent]:
    """Analyze a request for security threats"""
    events = await ids.analyze_request(request_data)

    if events:
        await alert_manager.process_security_events(events)

    return events


async def check_ip_reputation(ip: str) -> Dict[str, Any]:
    """Check IP reputation using threat intelligence"""
    return await threat_intelligence.check_ip_threat_level(ip)


def block_suspicious_ip(ip: str, reason: str, duration: int = 3600):
    """Block a suspicious IP address"""
    ids.block_ip(ip, reason, duration)
    threat_intelligence.add_to_threat_db(ip, reason)
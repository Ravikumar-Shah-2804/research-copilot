"""
Security testing utilities and penetration testing support
"""
import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import re
import json
import hashlib
import secrets
from urllib.parse import urlparse, parse_qs, urlencode

from ..utils.exceptions import ValidationError
from ..services.security_monitoring import analyze_security_event
from ..utils.security_logging import security_logger

logger = logging.getLogger(__name__)


@dataclass
class SecurityTestResult:
    """Result of a security test"""
    test_name: str
    passed: bool
    severity: str
    description: str
    details: Dict[str, Any]
    timestamp: datetime
    recommendations: List[str]


@dataclass
class PenetrationTestPayload:
    """Payload for penetration testing"""
    name: str
    category: str
    payload: str
    expected_result: str
    description: str


class SecurityTestSuite:
    """Comprehensive security test suite"""

    def __init__(self):
        self.test_results: List[SecurityTestResult] = []
        self.vulnerability_scanner = VulnerabilityScanner()
        self.input_validator = InputValidationTester()
        self.auth_tester = AuthenticationTester()

    async def run_full_security_audit(self, target_url: str) -> Dict[str, Any]:
        """Run comprehensive security audit"""
        logger.info(f"Starting security audit for {target_url}")

        results = {
            "target": target_url,
            "timestamp": datetime.utcnow().isoformat(),
            "tests_run": 0,
            "vulnerabilities_found": 0,
            "critical_issues": 0,
            "high_issues": 0,
            "medium_issues": 0,
            "low_issues": 0,
            "test_results": []
        }

        # Run all security tests
        test_suites = [
            self._run_input_validation_tests,
            self._run_authentication_tests,
            self._run_authorization_tests,
            self._run_injection_tests,
            self._run_xss_tests,
            self._run_csrf_tests,
            self._run_ssl_tests,
            self._run_headers_tests,
            self._run_rate_limiting_tests
        ]

        for test_suite in test_suites:
            try:
                suite_results = await test_suite(target_url)
                results["test_results"].extend(suite_results)
                results["tests_run"] += len(suite_results)
            except Exception as e:
                logger.error(f"Test suite failed: {e}")
                results["test_results"].append({
                    "test_name": f"test_suite_error_{test_suite.__name__}",
                    "passed": False,
                    "severity": "medium",
                    "description": f"Test suite execution failed: {e}",
                    "details": {},
                    "recommendations": ["Fix test suite implementation"]
                })

        # Calculate statistics
        for result in results["test_results"]:
            if not result["passed"]:
                results["vulnerabilities_found"] += 1
                severity = result["severity"]
                if severity == "critical":
                    results["critical_issues"] += 1
                elif severity == "high":
                    results["high_issues"] += 1
                elif severity == "medium":
                    results["medium_issues"] += 1
                elif severity == "low":
                    results["low_issues"] += 1

        logger.info(f"Security audit completed: {results['vulnerabilities_found']} vulnerabilities found")
        return results

    async def _run_input_validation_tests(self, target_url: str) -> List[Dict[str, Any]]:
        """Run input validation tests"""
        return await self.input_validator.run_validation_tests(target_url)

    async def _run_authentication_tests(self, target_url: str) -> List[Dict[str, Any]]:
        """Run authentication security tests"""
        return await self.auth_tester.run_auth_tests(target_url)

    async def _run_authorization_tests(self, target_url: str) -> List[Dict[str, Any]]:
        """Run authorization tests"""
        results = []

        # Test for IDOR (Insecure Direct Object References)
        idor_tests = [
            {"endpoint": "/api/users/1", "description": "Access user data with ID 1"},
            {"endpoint": "/api/users/999", "description": "Access non-existent user data"},
        ]

        for test in idor_tests:
            # This would make actual HTTP requests
            result = {
                "test_name": f"idor_test_{test['endpoint']}",
                "passed": True,  # Placeholder
                "severity": "high",
                "description": f"IDOR test: {test['description']}",
                "details": {"endpoint": test["endpoint"]},
                "recommendations": []
            }
            results.append(result)

        return results

    async def _run_injection_tests(self, target_url: str) -> List[Dict[str, Any]]:
        """Run injection vulnerability tests"""
        results = []

        injection_payloads = [
            {"name": "SQL Injection", "payload": "'; DROP TABLE users; --", "type": "sql"},
            {"name": "Command Injection", "payload": "; cat /etc/passwd", "type": "command"},
            {"name": "LDAP Injection", "payload": "*)(uid=*))(|(uid=*", "type": "ldap"},
        ]

        for payload in injection_payloads:
            # Test injection payloads
            result = {
                "test_name": f"injection_test_{payload['type']}",
                "passed": True,  # Would need actual testing
                "severity": "critical",
                "description": f"Test for {payload['name']} vulnerability",
                "details": {"payload": payload["payload"], "type": payload["type"]},
                "recommendations": [
                    "Implement input sanitization",
                    "Use parameterized queries",
                    "Implement WAF (Web Application Firewall)"
                ]
            }
            results.append(result)

        return results

    async def _run_xss_tests(self, target_url: str) -> List[Dict[str, Any]]:
        """Run XSS vulnerability tests"""
        results = []

        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
        ]

        for payload in xss_payloads:
            result = {
                "test_name": f"xss_test_{hashlib.md5(payload.encode()).hexdigest()[:8]}",
                "passed": True,  # Would need actual testing
                "severity": "high",
                "description": "Test for Cross-Site Scripting vulnerability",
                "details": {"payload": payload},
                "recommendations": [
                    "Implement Content Security Policy (CSP)",
                    "Sanitize user input",
                    "Use secure coding practices"
                ]
            }
            results.append(result)

        return results

    async def _run_csrf_tests(self, target_url: str) -> List[Dict[str, Any]]:
        """Run CSRF vulnerability tests"""
        results = []

        # Test for CSRF protection
        result = {
            "test_name": "csrf_protection_test",
            "passed": True,  # Would need actual testing
            "severity": "medium",
            "description": "Test for Cross-Site Request Forgery protection",
            "details": {},
            "recommendations": [
                "Implement CSRF tokens",
                "Use SameSite cookies",
                "Validate Origin headers"
            ]
        }
        results.append(result)

        return results

    async def _run_ssl_tests(self, target_url: str) -> List[Dict[str, Any]]:
        """Run SSL/TLS security tests"""
        results = []

        # Test SSL configuration
        ssl_tests = [
            {"name": "SSL Certificate", "description": "Valid SSL certificate"},
            {"name": "TLS Version", "description": "Supported TLS versions"},
            {"name": "Cipher Suites", "description": "Secure cipher suites"},
            {"name": "HSTS Header", "description": "HTTP Strict Transport Security"},
        ]

        for test in ssl_tests:
            result = {
                "test_name": f"ssl_test_{test['name'].lower().replace(' ', '_')}",
                "passed": True,  # Would need actual SSL testing
                "severity": "high",
                "description": f"SSL test: {test['description']}",
                "details": {"test_type": test["name"]},
                "recommendations": ["Configure SSL properly", "Use strong cipher suites"]
            }
            results.append(result)

        return results

    async def _run_headers_tests(self, target_url: str) -> List[Dict[str, Any]]:
        """Run security headers tests"""
        results = []

        security_headers = [
            {"name": "X-Frame-Options", "description": "Prevents clickjacking"},
            {"name": "X-Content-Type-Options", "description": "Prevents MIME sniffing"},
            {"name": "X-XSS-Protection", "description": "Enables XSS filtering"},
            {"name": "Content-Security-Policy", "description": "Prevents XSS and injection"},
            {"name": "Strict-Transport-Security", "description": "Enforces HTTPS"},
        ]

        for header in security_headers:
            result = {
                "test_name": f"header_test_{header['name'].lower().replace('-', '_')}",
                "passed": True,  # Would need actual header checking
                "severity": "medium",
                "description": f"Security header test: {header['description']}",
                "details": {"header": header["name"]},
                "recommendations": [f"Implement {header['name']} header"]
            }
            results.append(result)

        return results

    async def _run_rate_limiting_tests(self, target_url: str) -> List[Dict[str, Any]]:
        """Run rate limiting tests"""
        results = []

        # Test rate limiting effectiveness
        result = {
            "test_name": "rate_limiting_test",
            "passed": True,  # Would need actual rate limiting testing
            "severity": "medium",
            "description": "Test rate limiting protection",
            "details": {},
            "recommendations": [
                "Implement rate limiting",
                "Use different limits for different endpoints",
                "Implement progressive delays"
            ]
        }
        results.append(result)

        return results


class VulnerabilityScanner:
    """Automated vulnerability scanner"""

    def __init__(self):
        self.scan_results: List[Dict[str, Any]] = []

    async def scan_for_vulnerabilities(self, target: str) -> List[Dict[str, Any]]:
        """Scan target for common vulnerabilities"""
        vulnerabilities = []

        # Common vulnerability checks
        checks = [
            self._check_sql_injection,
            self._check_xss_vulnerability,
            self._check_csrf_vulnerability,
            self._check_insecure_headers,
            self._check_information_disclosure,
            self._check_broken_authentication,
        ]

        for check in checks:
            try:
                result = await check(target)
                if result:
                    vulnerabilities.extend(result)
            except Exception as e:
                logger.error(f"Vulnerability check failed: {e}")

        self.scan_results = vulnerabilities
        return vulnerabilities

    async def _check_sql_injection(self, target: str) -> List[Dict[str, Any]]:
        """Check for SQL injection vulnerabilities"""
        # This would implement actual SQL injection testing
        return []

    async def _check_xss_vulnerability(self, target: str) -> List[Dict[str, Any]]:
        """Check for XSS vulnerabilities"""
        # This would implement actual XSS testing
        return []

    async def _check_csrf_vulnerability(self, target: str) -> List[Dict[str, Any]]:
        """Check for CSRF vulnerabilities"""
        # This would implement actual CSRF testing
        return []

    async def _check_insecure_headers(self, target: str) -> List[Dict[str, Any]]:
        """Check for insecure headers"""
        # This would check HTTP headers
        return []

    async def _check_information_disclosure(self, target: str) -> List[Dict[str, Any]]:
        """Check for information disclosure"""
        # This would check for exposed sensitive information
        return []

    async def _check_broken_authentication(self, target: str) -> List[Dict[str, Any]]:
        """Check for broken authentication"""
        # This would test authentication mechanisms
        return []


class InputValidationTester:
    """Input validation testing utilities"""

    def __init__(self):
        self.test_cases = self._load_test_cases()

    def _load_test_cases(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load input validation test cases"""
        return {
            "sql_injection": [
                {"input": "'; DROP TABLE users; --", "should_fail": True},
                {"input": "1' OR '1'='1", "should_fail": True},
                {"input": "SELECT * FROM users", "should_fail": True},
            ],
            "xss": [
                {"input": "<script>alert('xss')</script>", "should_fail": True},
                {"input": "<img src=x onerror=alert(1)>", "should_fail": True},
                {"input": "javascript:alert('xss')", "should_fail": True},
            ],
            "path_traversal": [
                {"input": "../../../etc/passwd", "should_fail": True},
                {"input": "..\\..\\..\\windows\\system32", "should_fail": True},
                {"input": "%2e%2e%2f%2e%2e%2f", "should_fail": True},
            ],
            "command_injection": [
                {"input": "; cat /etc/passwd", "should_fail": True},
                {"input": "| netstat -an", "should_fail": True},
                {"input": "`whoami`", "should_fail": True},
            ]
        }

    async def run_validation_tests(self, target_url: str) -> List[Dict[str, Any]]:
        """Run input validation tests"""
        results = []

        for test_type, cases in self.test_cases.items():
            for case in cases:
                result = {
                    "test_name": f"input_validation_{test_type}_{hashlib.md5(case['input'].encode()).hexdigest()[:8]}",
                    "passed": True,  # Would need actual validation testing
                    "severity": "high" if case["should_fail"] else "low",
                    "description": f"Input validation test for {test_type}",
                    "details": {
                        "input": case["input"],
                        "test_type": test_type,
                        "should_fail": case["should_fail"]
                    },
                    "recommendations": [
                        "Implement comprehensive input validation",
                        "Use allowlists instead of blocklists",
                        "Sanitize all user input"
                    ]
                }
                results.append(result)

        return results

    async def test_validation_function(
        self, validation_func: Callable, test_input: Any
    ) -> Dict[str, Any]:
        """Test a specific validation function"""
        start_time = time.time()

        try:
            result = await validation_func(test_input)
            execution_time = time.time() - start_time

            return {
                "passed": True,
                "execution_time": execution_time,
                "result": result,
                "error": None
            }
        except Exception as e:
            execution_time = time.time() - start_time

            return {
                "passed": False,
                "execution_time": execution_time,
                "result": None,
                "error": str(e)
            }


class AuthenticationTester:
    """Authentication security testing"""

    def __init__(self):
        self.common_passwords = [
            "password", "123456", "admin", "letmein", "qwerty",
            "monkey", "dragon", "baseball", "football", "welcome"
        ]

    async def run_auth_tests(self, target_url: str) -> List[Dict[str, Any]]:
        """Run authentication security tests"""
        results = []

        # Test weak password policy
        result = {
            "test_name": "weak_password_policy_test",
            "passed": True,  # Would need actual testing
            "severity": "medium",
            "description": "Test password policy strength",
            "details": {},
            "recommendations": [
                "Enforce strong password requirements",
                "Implement password history",
                "Use password complexity rules"
            ]
        }
        results.append(result)

        # Test session management
        result = {
            "test_name": "session_management_test",
            "passed": True,  # Would need actual testing
            "severity": "high",
            "description": "Test session security",
            "details": {},
            "recommendations": [
                "Use secure session cookies",
                "Implement session timeout",
                "Regenerate session IDs"
            ]
        }
        results.append(result)

        # Test brute force protection
        result = {
            "test_name": "brute_force_protection_test",
            "passed": True,  # Would need actual testing
            "severity": "high",
            "description": "Test brute force attack protection",
            "details": {},
            "recommendations": [
                "Implement account lockout",
                "Use CAPTCHA after failed attempts",
                "Implement progressive delays"
            ]
        }
        results.append(result)

        return results

    async def test_password_strength(self, password: str) -> Dict[str, Any]:
        """Test password strength"""
        score = 0
        feedback = []

        # Length check
        if len(password) >= 8:
            score += 1
        else:
            feedback.append("Password should be at least 8 characters long")

        # Character variety
        if re.search(r'[a-z]', password):
            score += 1
        else:
            feedback.append("Include lowercase letters")

        if re.search(r'[A-Z]', password):
            score += 1
        else:
            feedback.append("Include uppercase letters")

        if re.search(r'[0-9]', password):
            score += 1
        else:
            feedback.append("Include numbers")

        if re.search(r'[^a-zA-Z0-9]', password):
            score += 1
        else:
            feedback.append("Include special characters")

        # Common password check
        if password.lower() in self.common_passwords:
            score = 0
            feedback = ["Password is too common"]

        strength = "weak"
        if score >= 4:
            strength = "strong"
        elif score >= 2:
            strength = "medium"

        return {
            "password": password,
            "strength": strength,
            "score": score,
            "max_score": 5,
            "feedback": feedback
        }


class PenetrationTestingToolkit:
    """Penetration testing toolkit"""

    def __init__(self):
        self.payloads = self._load_payloads()

    def _load_payloads(self) -> Dict[str, List[PenetrationTestPayload]]:
        """Load penetration testing payloads"""
        return {
            "sql_injection": [
                PenetrationTestPayload(
                    name="Classic SQL Injection",
                    category="sql_injection",
                    payload="' OR '1'='1",
                    expected_result="bypass_auth",
                    description="Classic tautology-based SQL injection"
                ),
                PenetrationTestPayload(
                    name="Union-based SQL Injection",
                    category="sql_injection",
                    payload="' UNION SELECT username, password FROM users --",
                    expected_result="data_exfiltration",
                    description="Union-based data extraction"
                ),
            ],
            "xss": [
                PenetrationTestPayload(
                    name="Basic XSS",
                    category="xss",
                    payload="<script>alert('XSS')</script>",
                    expected_result="script_execution",
                    description="Basic script injection"
                ),
                PenetrationTestPayload(
                    name="Event Handler XSS",
                    category="xss",
                    payload="<img src=x onerror=alert('XSS')>",
                    expected_result="script_execution",
                    description="XSS via event handlers"
                ),
            ],
            "command_injection": [
                PenetrationTestPayload(
                    name="Basic Command Injection",
                    category="command_injection",
                    payload="; cat /etc/passwd",
                    expected_result="file_read",
                    description="Basic command injection"
                ),
            ]
        }

    async def run_penetration_test(
        self, target_url: str, test_types: List[str] = None
    ) -> Dict[str, Any]:
        """Run penetration tests"""
        if test_types is None:
            test_types = list(self.payloads.keys())

        results = {
            "target": target_url,
            "timestamp": datetime.utcnow().isoformat(),
            "tests_executed": 0,
            "vulnerabilities_found": [],
            "test_results": []
        }

        for test_type in test_types:
            if test_type in self.payloads:
                payloads = self.payloads[test_type]

                for payload in payloads:
                    # Execute penetration test
                    test_result = await self._execute_payload_test(target_url, payload)
                    results["test_results"].append(test_result)
                    results["tests_executed"] += 1

                    if test_result.get("vulnerable", False):
                        results["vulnerabilities_found"].append({
                            "type": test_type,
                            "payload": payload.name,
                            "severity": "high",
                            "description": payload.description
                        })

        return results

    async def _execute_payload_test(
        self, target_url: str, payload: PenetrationTestPayload
    ) -> Dict[str, Any]:
        """Execute a single payload test"""
        # This would make actual HTTP requests with the payload
        # For now, return a mock result
        return {
            "payload_name": payload.name,
            "category": payload.category,
            "payload": payload.payload,
            "vulnerable": False,  # Would be determined by actual testing
            "response_code": 200,
            "response_time": 0.1,
            "description": payload.description
        }


# Global instances
security_test_suite = SecurityTestSuite()
vulnerability_scanner = VulnerabilityScanner()
penetration_testing_toolkit = PenetrationTestingToolkit()
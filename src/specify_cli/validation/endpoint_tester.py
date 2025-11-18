"""
Endpoint Testing Module for Bicep Validate Command

This module tests deployed API endpoints using async HTTP requests with retry logic,
concurrent testing, and response validation.

Part of User Story 3: Test Deployment and Endpoint Validation
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from enum import Enum
import httpx

from specify_cli.validation.endpoint_discoverer import Endpoint
from specify_cli.utils.retry_policies import ExponentialBackoff

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Endpoint test result status"""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    AUTH_ERROR = "auth_error"
    SERVER_ERROR = "server_error"
    SKIPPED = "skipped"


@dataclass
class TestResult:
    """Result from testing an endpoint"""
    
    endpoint: Endpoint
    status: TestStatus
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    response_body: Optional[str] = None
    retry_count: int = 0
    
    def __str__(self) -> str:
        """String representation for logging"""
        status_marker = "✓" if self.status == TestStatus.SUCCESS else "✗"
        time_info = f" ({self.response_time_ms:.0f}ms)" if self.response_time_ms else ""
        return f"{status_marker} {self.endpoint}{time_info}"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "endpoint": self.endpoint.to_dict(),
            "status": self.status.value,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
        }


class EndpointTester:
    """Tests deployed API endpoints with retry logic and concurrent execution"""
    
    def __init__(
        self,
        base_url: str,
        timeout_seconds: int = 30,
        max_concurrent: int = 10,
        retry_policy: Optional[ExponentialBackoff] = None,
        auth_token: Optional[str] = None,
        skip_auth_endpoints: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize endpoint tester
        
        Args:
            base_url: Base URL of deployed application (e.g., https://myapp.azurewebsites.net)
            timeout_seconds: HTTP request timeout in seconds
            max_concurrent: Maximum number of concurrent tests
            retry_policy: Retry policy for failed requests (default: 3 attempts)
            auth_token: Optional authentication token (Bearer token)
            skip_auth_endpoints: Skip testing endpoints that require authentication
            verbose: Enable verbose logging (detailed HTTP request/response)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout_seconds = timeout_seconds
        self.max_concurrent = max_concurrent
        self.retry_policy = retry_policy or ExponentialBackoff(base_delay=2.0, max_delay=30.0, max_attempts=3)
        self.auth_token = auth_token
        self.skip_auth_endpoints = skip_auth_endpoints
        self.verbose = verbose
        
        # Semaphore for concurrent request limiting
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        # Shared HTTP client with connection pooling (for performance)
        # Limits: connections per host and total connections
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
        self._http_client: Optional[httpx.AsyncClient] = None
        self._client_limits = limits
        
        logger.info(f"Initialized EndpointTester for: {self.base_url}")
        logger.info(f"Config: timeout={timeout_seconds}s, max_concurrent={max_concurrent}, retries={self.retry_policy.max_attempts}")
    
    def filter_endpoints(
        self,
        endpoints: List[Endpoint],
        methods: Optional[List[str]] = None,
        path_pattern: Optional[str] = None,
    ) -> List[Endpoint]:
        """
        Filter endpoints by HTTP method and path pattern
        
        Args:
            endpoints: List of endpoints to filter
            methods: Optional list of HTTP methods to include (e.g., ['GET', 'POST'])
            path_pattern: Optional regex pattern to match against paths
        
        Returns:
            Filtered list of endpoints
        """
        import re
        
        filtered = endpoints
        
        # Filter by HTTP method
        if methods:
            methods_upper = [m.upper() for m in methods]
            filtered = [ep for ep in filtered if ep.method.upper() in methods_upper]
            logger.info(f"Filtered by methods {methods_upper}: {len(filtered)} endpoints")
        
        # Filter by path pattern
        if path_pattern:
            pattern = re.compile(path_pattern)
            filtered = [ep for ep in filtered if pattern.search(ep.path)]
            logger.info(f"Filtered by pattern '{path_pattern}': {len(filtered)} endpoints")
        
        return filtered
    
    async def _get_or_create_client(self, timeout: float) -> httpx.AsyncClient:
        """
        Get or create shared HTTP client with connection pooling (for performance).
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            Configured AsyncClient instance with connection pooling
        """
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=timeout,
                limits=self._client_limits,
                follow_redirects=False  # Don't follow redirects automatically
            )
            logger.debug(f"Created shared HTTP client (timeout={timeout}s, limits={self._client_limits})")
        return self._http_client
    
    async def close(self) -> None:
        """Close shared HTTP client and release connection pool resources."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
            logger.debug("Closed shared HTTP client and released connections")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - ensures client cleanup."""
        await self.close()
        return False
    
    async def test_endpoint(
        self,
        endpoint: Endpoint,
        expected_status_codes: Optional[Set[int]] = None,
        timeout_seconds: Optional[int] = None,
    ) -> TestResult:
        """
        Test a single endpoint
        
        Args:
            endpoint: Endpoint to test
            expected_status_codes: Set of acceptable status codes (default: 200-299)
            timeout_seconds: Override timeout for this test (default: use instance timeout)
        
        Returns:
            Test result
        """
        if expected_status_codes is None:
            expected_status_codes = set(range(200, 300))
        
        # Use provided timeout or fall back to instance timeout
        timeout = timeout_seconds if timeout_seconds is not None else self.timeout_seconds
        
        # Construct full URL
        url = f"{self.base_url}{endpoint.path}"
        
        # Prepare headers
        headers = {}
        if endpoint.requires_auth and self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        logger.info(f"Testing: {endpoint.method} {url}")
        if self.verbose:
            logger.info(f"  Request timeout: {timeout}s")
            logger.info(f"  Expected status codes: {expected_status_codes}")
            if headers:
                logger.info(f"  Headers: {list(headers.keys())}")
        
        # Test with retry logic
        retry_count = 0
        last_error = None
        
        async with self._semaphore:
            # Get or create shared HTTP client (reuses connections for performance)
            client = await self._get_or_create_client(timeout)
            
            for attempt in range(self.retry_policy.max_attempts):
                try:
                    # Make HTTP request using shared client
                    start_time = asyncio.get_event_loop().time()
                    
                    response = await self._make_request(
                        client, endpoint.method, url, headers
                    )
                    
                    end_time = asyncio.get_event_loop().time()
                    response_time_ms = (end_time - start_time) * 1000
                    
                    # Validate response
                    if response.status_code in expected_status_codes:
                        logger.info(f"✓ {endpoint} -> {response.status_code} ({response_time_ms:.0f}ms)")
                        if self.verbose:
                            logger.info(f"  Response headers: {dict(response.headers)}")
                            logger.info(f"  Response body preview: {response.text[:200] if response.text else '(empty)'}")
                        return TestResult(
                            endpoint=endpoint,
                            status=TestStatus.SUCCESS,
                            status_code=response.status_code,
                            response_time_ms=response_time_ms,
                            retry_count=retry_count,
                        )
                    else:
                        # Unexpected status code
                        status = self._classify_status_code(response.status_code)
                        error_msg = f"Unexpected status code: {response.status_code}"
                        
                        logger.warning(f"✗ {endpoint} -> {response.status_code} (expected {expected_status_codes})")
                        
                        return TestResult(
                            endpoint=endpoint,
                            status=status,
                            status_code=response.status_code,
                            response_time_ms=response_time_ms,
                            error_message=error_msg,
                            retry_count=retry_count,
                        )
                
                except httpx.TimeoutException as e:
                    retry_count += 1
                    last_error = str(e)
                    
                    if attempt < self.retry_policy.max_attempts - 1:
                        delay = self.retry_policy.get_delay(attempt)
                        logger.warning(f"Request timeout (attempt {attempt + 1}), retrying in {delay:.1f}s...")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"✗ {endpoint} -> Timeout after {retry_count} attempts")
                
                except httpx.HTTPError as e:
                    retry_count += 1
                    last_error = str(e)
                    
                    if attempt < self.retry_policy.max_attempts - 1:
                        delay = self.retry_policy.get_delay(attempt)
                        logger.warning(f"HTTP error (attempt {attempt + 1}), retrying in {delay:.1f}s...")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"✗ {endpoint} -> HTTP error after {retry_count} attempts: {e}")
                
                except Exception as e:
                    retry_count += 1
                    last_error = str(e)
                    logger.error(f"✗ {endpoint} -> Unexpected error: {e}")
                    break  # Don't retry on unexpected errors
        
        # All retries exhausted or unexpected error
        return TestResult(
            endpoint=endpoint,
            status=TestStatus.TIMEOUT if last_error and "timeout" in last_error.lower() else TestStatus.FAILURE,
            error_message=last_error or "Request failed",
            retry_count=retry_count,
        )
    
    async def test_multiple_endpoints(
        self,
        endpoints: List[Endpoint],
        expected_status_codes: Optional[Set[int]] = None,
        skip_auth_endpoints: bool = False,
        timeout_seconds: Optional[int] = None,
    ) -> List[TestResult]:
        """
        Test multiple endpoints concurrently
        
        Args:
            endpoints: List of endpoints to test
            expected_status_codes: Set of acceptable status codes (default: 200-299)
            skip_auth_endpoints: If True, skip endpoints that require authentication
            timeout_seconds: Override timeout for all tests (default: use instance timeout)
        
        Returns:
            List of test results
        """
        logger.info(f"Testing {len(endpoints)} endpoints (max {self.max_concurrent} concurrent)...")
        
        # Filter endpoints if needed
        endpoints_to_test = endpoints
        if skip_auth_endpoints:
            endpoints_to_test = [e for e in endpoints if not e.requires_auth]
            skipped_count = len(endpoints) - len(endpoints_to_test)
            if skipped_count > 0:
                logger.info(f"Skipping {skipped_count} authenticated endpoints")
        
        # Create test tasks
        tasks = [
            self.test_endpoint(endpoint, expected_status_codes, timeout_seconds)
            for endpoint in endpoints_to_test
        ]
        
        # Execute tests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Add skipped results
        if skip_auth_endpoints:
            for endpoint in endpoints:
                if endpoint.requires_auth:
                    results.append(TestResult(
                        endpoint=endpoint,
                        status=TestStatus.SKIPPED,
                        error_message="Authentication required (skipped)",
                    ))
        
        # Log summary
        success_count = sum(1 for r in results if r.status == TestStatus.SUCCESS)
        failure_count = sum(1 for r in results if r.status in [TestStatus.FAILURE, TestStatus.TIMEOUT, TestStatus.AUTH_ERROR, TestStatus.SERVER_ERROR])
        skipped_count = sum(1 for r in results if r.status == TestStatus.SKIPPED)
        
        logger.info(f"Test summary: {success_count} passed, {failure_count} failed, {skipped_count} skipped")
        
        return results
    
    async def _make_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        headers: Dict[str, str],
    ) -> httpx.Response:
        """Make HTTP request with specified method"""
        method_upper = method.upper()
        
        if method_upper == 'GET':
            return await client.get(url, headers=headers)
        elif method_upper == 'POST':
            return await client.post(url, headers=headers, json={})
        elif method_upper == 'PUT':
            return await client.put(url, headers=headers, json={})
        elif method_upper == 'DELETE':
            return await client.delete(url, headers=headers)
        elif method_upper == 'PATCH':
            return await client.patch(url, headers=headers, json={})
        elif method_upper == 'HEAD':
            return await client.head(url, headers=headers)
        elif method_upper == 'OPTIONS':
            return await client.options(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    
    def _classify_status_code(self, status_code: int) -> TestStatus:
        """Classify HTTP status code into test status"""
        if status_code in [401, 403]:
            return TestStatus.AUTH_ERROR
        elif status_code >= 500:
            return TestStatus.SERVER_ERROR
        else:
            return TestStatus.FAILURE
    
    def get_failed_results(self, results: List[TestResult]) -> List[TestResult]:
        """Get all failed test results"""
        return [
            r for r in results
            if r.status in [TestStatus.FAILURE, TestStatus.TIMEOUT, TestStatus.AUTH_ERROR, TestStatus.SERVER_ERROR]
        ]
    
    def get_successful_results(self, results: List[TestResult]) -> List[TestResult]:
        """Get all successful test results"""
        return [r for r in results if r.status == TestStatus.SUCCESS]
    
    def calculate_success_rate(self, results: List[TestResult]) -> float:
        """Calculate success rate (0.0 to 1.0)"""
        if not results:
            return 0.0
        
        # Don't count skipped endpoints
        testable_results = [r for r in results if r.status != TestStatus.SKIPPED]
        if not testable_results:
            return 0.0
        
        success_count = sum(1 for r in testable_results if r.status == TestStatus.SUCCESS)
        return success_count / len(testable_results)

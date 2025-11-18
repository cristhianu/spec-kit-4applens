"""
Unit tests for EndpointTester module

Tests async HTTP endpoint testing with retry logic, concurrent execution,
and response validation.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from specify_cli.validation.endpoint_discoverer import Endpoint
from specify_cli.validation.endpoint_tester import EndpointTester, TestResult, TestStatus
from specify_cli.utils.retry_policies import ExponentialBackoff


class TestEndpointTester:
    """Test EndpointTester class"""
    
    def test_initialization(self):
        """Test tester initialization"""
        tester = EndpointTester(
            base_url="https://myapp.azurewebsites.net",
            timeout_seconds=30,
            max_concurrent=10,
        )
        
        assert tester.base_url == "https://myapp.azurewebsites.net"
        assert tester.timeout_seconds == 30
        assert tester.max_concurrent == 10
        assert tester.retry_policy.max_attempts == 3
    
    @pytest.mark.asyncio
    async def test_test_endpoint_success(self):
        """Test successful endpoint test"""
        endpoint = Endpoint(method="GET", path="/api/health")
        tester = EndpointTester(base_url="https://example.com")
        
        # Mock httpx response
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch.object(httpx.AsyncClient, 'get', return_value=mock_response):
            result = await tester.test_endpoint(endpoint)
        
        assert result.status == TestStatus.SUCCESS
        assert result.status_code == 200
        assert result.endpoint == endpoint
        assert result.retry_count == 0
    
    @pytest.mark.asyncio
    async def test_test_endpoint_with_custom_expected_codes(self):
        """Test endpoint with custom expected status codes"""
        endpoint = Endpoint(method="GET", path="/api/users")
        tester = EndpointTester(base_url="https://example.com")
        
        # Mock 201 response
        mock_response = MagicMock()
        mock_response.status_code = 201
        
        with patch.object(httpx.AsyncClient, 'get', return_value=mock_response):
            # Accept 200-201
            result = await tester.test_endpoint(endpoint, expected_status_codes={200, 201})
        
        assert result.status == TestStatus.SUCCESS
        assert result.status_code == 201
    
    @pytest.mark.asyncio
    async def test_test_endpoint_auth_error(self):
        """Test endpoint returning authentication error"""
        endpoint = Endpoint(method="GET", path="/api/secure", requires_auth=True)
        tester = EndpointTester(base_url="https://example.com")
        
        # Mock 401 response
        mock_response = MagicMock()
        mock_response.status_code = 401
        
        with patch.object(httpx.AsyncClient, 'get', return_value=mock_response):
            result = await tester.test_endpoint(endpoint)
        
        assert result.status == TestStatus.AUTH_ERROR
        assert result.status_code == 401
    
    @pytest.mark.asyncio
    async def test_test_endpoint_server_error(self):
        """Test endpoint returning server error"""
        endpoint = Endpoint(method="GET", path="/api/error")
        tester = EndpointTester(base_url="https://example.com")
        
        # Mock 500 response
        mock_response = MagicMock()
        mock_response.status_code = 500
        
        with patch.object(httpx.AsyncClient, 'get', return_value=mock_response):
            result = await tester.test_endpoint(endpoint)
        
        assert result.status == TestStatus.SERVER_ERROR
        assert result.status_code == 500
    
    @pytest.mark.asyncio
    async def test_test_endpoint_timeout_with_retry(self):
        """Test endpoint timeout with retry logic"""
        endpoint = Endpoint(method="GET", path="/api/slow")
        tester = EndpointTester(
            base_url="https://example.com",
            retry_policy=ExponentialBackoff(max_attempts=2, base_delay=0.1),  # Fast retries for testing
        )
        
        # Mock timeout on all attempts
        with patch.object(httpx.AsyncClient, 'get', side_effect=httpx.TimeoutException("Request timeout")):
            result = await tester.test_endpoint(endpoint)
        
        assert result.status == TestStatus.TIMEOUT
        assert result.retry_count == 2  # 2 retries after initial attempt
        assert "timeout" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_test_endpoint_http_methods(self):
        """Test different HTTP methods"""
        tester = EndpointTester(base_url="https://example.com")
        
        # Mock responses for different methods
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        methods_to_test = [
            ("GET", "get"),
            ("POST", "post"),
            ("PUT", "put"),
            ("DELETE", "delete"),
            ("PATCH", "patch"),
        ]
        
        for method, client_method_name in methods_to_test:
            endpoint = Endpoint(method=method, path="/api/test")
            
            # Create async mock that returns the response
            async_mock = AsyncMock(return_value=mock_response)
            
            with patch.object(httpx.AsyncClient, client_method_name, async_mock):
                result = await tester.test_endpoint(endpoint)
            
            assert result.status == TestStatus.SUCCESS
            assert result.status_code == 200
    
    @pytest.mark.asyncio
    async def test_test_endpoint_with_auth_token(self):
        """Test endpoint with authentication token"""
        endpoint = Endpoint(method="GET", path="/api/secure", requires_auth=True)
        tester = EndpointTester(
            base_url="https://example.com",
            auth_token="test_token_12345",
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        async def check_auth_header(*args, **kwargs):
            # Verify Bearer token is included
            headers = kwargs.get('headers', {})
            assert headers.get('Authorization') == 'Bearer test_token_12345'
            return mock_response
        
        with patch.object(httpx.AsyncClient, 'get', side_effect=check_auth_header):
            result = await tester.test_endpoint(endpoint)
        
        assert result.status == TestStatus.SUCCESS
    
    @pytest.mark.asyncio
    async def test_test_multiple_endpoints_concurrent(self):
        """Test multiple endpoints with concurrent execution"""
        endpoints = [
            Endpoint(method="GET", path=f"/api/users/{i}")
            for i in range(5)
        ]
        
        tester = EndpointTester(base_url="https://example.com", max_concurrent=3)
        
        # Mock successful responses
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch.object(httpx.AsyncClient, 'get', return_value=mock_response):
            results = await tester.test_multiple_endpoints(endpoints)
        
        assert len(results) == 5
        assert all(r.status == TestStatus.SUCCESS for r in results)
    
    @pytest.mark.asyncio
    async def test_test_multiple_endpoints_skip_auth(self):
        """Test skipping authenticated endpoints"""
        endpoints = [
            Endpoint(method="GET", path="/api/public"),
            Endpoint(method="GET", path="/api/secure", requires_auth=True),
            Endpoint(method="GET", path="/api/admin", requires_auth=True),
        ]
        
        tester = EndpointTester(base_url="https://example.com")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch.object(httpx.AsyncClient, 'get', return_value=mock_response):
            results = await tester.test_multiple_endpoints(endpoints, skip_auth_endpoints=True)
        
        assert len(results) == 3
        
        # One successful test
        success_results = [r for r in results if r.status == TestStatus.SUCCESS]
        assert len(success_results) == 1
        
        # Two skipped
        skipped_results = [r for r in results if r.status == TestStatus.SKIPPED]
        assert len(skipped_results) == 2
    
    @pytest.mark.asyncio
    async def test_test_multiple_endpoints_mixed_results(self):
        """Test multiple endpoints with mixed success/failure"""
        endpoints = [
            Endpoint(method="GET", path="/api/success"),
            Endpoint(method="GET", path="/api/fail"),
            Endpoint(method="GET", path="/api/auth-error"),
        ]
        
        tester = EndpointTester(base_url="https://example.com")
        
        # Mock different responses
        responses = {
            "/api/success": MagicMock(status_code=200),
            "/api/fail": MagicMock(status_code=404),
            "/api/auth-error": MagicMock(status_code=403),
        }
        
        async def mock_get(*args, **kwargs):
            # Extract path from URL
            url = args[0] if args else kwargs.get('url', '')
            for path, response in responses.items():
                if path in url:
                    return response
            return MagicMock(status_code=500)
        
        with patch.object(httpx.AsyncClient, 'get', side_effect=mock_get):
            results = await tester.test_multiple_endpoints(endpoints)
        
        assert len(results) == 3
        
        # Check individual results
        success_count = sum(1 for r in results if r.status == TestStatus.SUCCESS)
        assert success_count == 1
        
        failure_count = sum(1 for r in results if r.status in [TestStatus.FAILURE, TestStatus.AUTH_ERROR])
        assert failure_count == 2
    
    def test_get_failed_results(self):
        """Test filtering failed results"""
        results = [
            TestResult(Endpoint("GET", "/api/a"), TestStatus.SUCCESS),
            TestResult(Endpoint("GET", "/api/b"), TestStatus.FAILURE),
            TestResult(Endpoint("GET", "/api/c"), TestStatus.AUTH_ERROR),
            TestResult(Endpoint("GET", "/api/d"), TestStatus.SKIPPED),
        ]
        
        tester = EndpointTester(base_url="https://example.com")
        failed = tester.get_failed_results(results)
        
        assert len(failed) == 2
        assert all(r.status in [TestStatus.FAILURE, TestStatus.AUTH_ERROR, TestStatus.TIMEOUT, TestStatus.SERVER_ERROR] for r in failed)
    
    def test_get_successful_results(self):
        """Test filtering successful results"""
        results = [
            TestResult(Endpoint("GET", "/api/a"), TestStatus.SUCCESS),
            TestResult(Endpoint("GET", "/api/b"), TestStatus.FAILURE),
            TestResult(Endpoint("GET", "/api/c"), TestStatus.SUCCESS),
        ]
        
        tester = EndpointTester(base_url="https://example.com")
        successful = tester.get_successful_results(results)
        
        assert len(successful) == 2
        assert all(r.status == TestStatus.SUCCESS for r in successful)
    
    def test_calculate_success_rate(self):
        """Test success rate calculation"""
        results = [
            TestResult(Endpoint("GET", "/api/a"), TestStatus.SUCCESS),
            TestResult(Endpoint("GET", "/api/b"), TestStatus.SUCCESS),
            TestResult(Endpoint("GET", "/api/c"), TestStatus.FAILURE),
            TestResult(Endpoint("GET", "/api/d"), TestStatus.SKIPPED),
        ]
        
        tester = EndpointTester(base_url="https://example.com")
        success_rate = tester.calculate_success_rate(results)
        
        # 2 success out of 3 testable (excluding skipped) = 66.67%
        assert success_rate == pytest.approx(2/3, rel=0.01)
    
    def test_calculate_success_rate_all_skipped(self):
        """Test success rate when all endpoints are skipped"""
        results = [
            TestResult(Endpoint("GET", "/api/a"), TestStatus.SKIPPED),
            TestResult(Endpoint("GET", "/api/b"), TestStatus.SKIPPED),
        ]
        
        tester = EndpointTester(base_url="https://example.com")
        success_rate = tester.calculate_success_rate(results)
        
        assert success_rate == 0.0
    
    def test_calculate_success_rate_empty(self):
        """Test success rate with no results"""
        tester = EndpointTester(base_url="https://example.com")
        success_rate = tester.calculate_success_rate([])
        
        assert success_rate == 0.0
    
    def test_test_result_string_representation(self):
        """Test TestResult __str__ method"""
        endpoint = Endpoint("GET", "/api/users")
        result = TestResult(
            endpoint=endpoint,
            status=TestStatus.SUCCESS,
            response_time_ms=123.45,
        )
        
        result_str = str(result)
        assert "✓" in result_str
        assert "GET" in result_str
        assert "/api/users" in result_str
        assert "123ms" in result_str or "123" in result_str
    
    def test_test_result_to_dict(self):
        """Test TestResult to_dict method"""
        endpoint = Endpoint("POST", "/api/products")
        result = TestResult(
            endpoint=endpoint,
            status=TestStatus.FAILURE,
            status_code=404,
            response_time_ms=250.5,
            error_message="Not found",
            retry_count=1,
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["status"] == "failure"
        assert result_dict["status_code"] == 404
        assert result_dict["response_time_ms"] == 250.5
        assert result_dict["error_message"] == "Not found"
        assert result_dict["retry_count"] == 1

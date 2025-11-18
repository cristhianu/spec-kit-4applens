"""
Unit tests for custom validation instructions (Phase 6)
Tests environment override, endpoint filtering, timeout override, and skip auth
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
from specify_cli.validation.validation_session import ValidationSession
from specify_cli.validation.endpoint_tester import EndpointTester, TestResult, TestStatus
from specify_cli.validation.endpoint_discoverer import Endpoint


class TestEnvironmentOverride:
    """Test custom environment override functionality"""
    
    def test_environment_parameter_accepted(self, tmp_path):
        """Test that ValidationSession accepts custom environment parameter"""
        session = ValidationSession(
            project_root=tmp_path,
            resource_group="test-rg",
            environment="production",
        )
        
        assert session.environment == "production"
    
    def test_environment_default_value(self, tmp_path):
        """Test that environment defaults to test-corp"""
        session = ValidationSession(
            project_root=tmp_path,
            resource_group="test-rg",
        )
        
        assert session.environment == "test-corp"
    
    def test_verbose_parameter_accepted(self, tmp_path):
        """Test that ValidationSession accepts verbose parameter"""
        session = ValidationSession(
            project_root=tmp_path,
            resource_group="test-rg",
            verbose=True,
        )
        
        assert session.verbose is True


class TestEndpointFiltering:
    """Test endpoint filtering by method and path pattern"""
    
    def test_filter_by_http_methods(self):
        """Test filtering endpoints by HTTP methods"""
        tester = EndpointTester(base_url="https://test.com")
        
        endpoints = [
            Endpoint(method="GET", path="/api/users", requires_auth=False),
            Endpoint(method="POST", path="/api/users", requires_auth=False),
            Endpoint(method="DELETE", path="/api/users/1", requires_auth=True),
            Endpoint(method="PUT", path="/api/users/1", requires_auth=True),
        ]
        
        # Filter for GET and POST only
        filtered = tester.filter_endpoints(endpoints, methods=["GET", "POST"])
        
        assert len(filtered) == 2
        assert all(e.method in ["GET", "POST"] for e in filtered)
    
    def test_filter_by_path_pattern(self):
        """Test filtering endpoints by regex path pattern"""
        tester = EndpointTester(base_url="https://test.com")
        
        endpoints = [
            Endpoint(method="GET", path="/api/users", requires_auth=False),
            Endpoint(method="GET", path="/api/products", requires_auth=False),
            Endpoint(method="GET", path="/health", requires_auth=False),
            Endpoint(method="GET", path="/metrics", requires_auth=False),
        ]
        
        # Filter for /api/* endpoints only
        filtered = tester.filter_endpoints(endpoints, path_pattern=r"^/api/")
        
        assert len(filtered) == 2
        assert all(e.path.startswith("/api/") for e in filtered)
    
    def test_filter_by_method_and_pattern(self):
        """Test filtering endpoints by both method and path pattern"""
        tester = EndpointTester(base_url="https://test.com")
        
        endpoints = [
            Endpoint(method="GET", path="/api/users", requires_auth=False),
            Endpoint(method="POST", path="/api/users", requires_auth=False),
            Endpoint(method="GET", path="/health", requires_auth=False),
            Endpoint(method="POST", path="/health", requires_auth=False),
        ]
        
        # Filter for GET requests to /api/* only
        filtered = tester.filter_endpoints(
            endpoints,
            methods=["GET"],
            path_pattern=r"^/api/"
        )
        
        assert len(filtered) == 1
        assert filtered[0].method == "GET"
        assert filtered[0].path == "/api/users"
    
    def test_filter_returns_empty_when_no_matches(self):
        """Test that filtering returns empty list when no endpoints match"""
        tester = EndpointTester(base_url="https://test.com")
        
        endpoints = [
            Endpoint(method="GET", path="/api/users", requires_auth=False),
            Endpoint(method="POST", path="/api/users", requires_auth=False),
        ]
        
        # Filter for DELETE methods (none exist)
        filtered = tester.filter_endpoints(endpoints, methods=["DELETE"])
        
        assert len(filtered) == 0


class TestCustomTestCriteria:
    """Test custom test criteria (status codes, timeouts)"""
    
    @pytest.mark.asyncio
    async def test_timeout_override_in_test_endpoint(self):
        """Test that timeout can be overridden per test"""
        tester = EndpointTester(
            base_url="https://test.com",
            timeout_seconds=30,  # Default timeout
        )
        
        endpoint = Endpoint(method="GET", path="/api/slow", requires_auth=False)
        
        # Mock the HTTP request
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock(spec=['status_code', 'text', 'headers'])
            mock_response.status_code = 200
            mock_response.text = "OK"
            mock_response.headers = {}
            
            # Mock all HTTP methods to return the mock_response
            async def mock_http_method(*args, **kwargs):
                return mock_response
            
            mock_client.get = mock_http_method
            mock_client.post = mock_http_method
            mock_client.put = mock_http_method
            mock_client.delete = mock_http_method
            mock_client.patch = mock_http_method
            mock_client.head = mock_http_method
            mock_client.options = mock_http_method
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Test with custom timeout (should be passed to AsyncClient)
            result = await tester.test_endpoint(endpoint, timeout_seconds=60)
            
            # Verify AsyncClient was called with custom timeout (and connection pooling params)
            mock_client_class.assert_called_once()
            call_kwargs = mock_client_class.call_args.kwargs
            assert call_kwargs['timeout'] == 60
            assert 'limits' in call_kwargs
            assert call_kwargs['follow_redirects'] is False
            assert result.status == TestStatus.SUCCESS
    
    @pytest.mark.asyncio
    async def test_expected_status_codes_override(self):
        """Test that expected status codes can be customized"""
        tester = EndpointTester(base_url="https://test.com")
        
        endpoint = Endpoint(method="POST", path="/api/users", requires_auth=False)
        
        # Mock HTTP client
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock(spec=['status_code', 'text', 'headers'])
            mock_response.status_code = 201  # Created
            mock_response.text = '{"id": 1}'
            mock_response.headers = {}
            
            # Mock all HTTP methods to return the mock_response
            async def mock_http_method(*args, **kwargs):
                return mock_response
            
            mock_client.get = mock_http_method
            mock_client.post = mock_http_method
            mock_client.put = mock_http_method
            mock_client.delete = mock_http_method
            mock_client.patch = mock_http_method
            mock_client.head = mock_http_method
            mock_client.options = mock_http_method
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Test accepting 201 as valid
            result = await tester.test_endpoint(
                endpoint,
                expected_status_codes={200, 201, 204}
            )
            
            assert result.status == TestStatus.SUCCESS
            assert result.status_code == 201


class TestSkipAuthentication:
    """Test skip authentication functionality"""
    
    def test_skip_auth_parameter_accepted(self):
        """Test that EndpointTester accepts skip_auth_endpoints parameter"""
        tester = EndpointTester(
            base_url="https://test.com",
            skip_auth_endpoints=True,
        )
        
        assert tester.skip_auth_endpoints is True
    
    @pytest.mark.asyncio
    async def test_skip_auth_endpoints_filters_correctly(self):
        """Test that skip_auth_endpoints filters out authenticated endpoints"""
        tester = EndpointTester(base_url="https://test.com")
        
        endpoints = [
            Endpoint(method="GET", path="/health", requires_auth=False),
            Endpoint(method="GET", path="/api/users", requires_auth=True),
            Endpoint(method="POST", path="/api/users", requires_auth=True),
        ]
        
        # Mock HTTP client
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock(spec=['status_code', 'text', 'headers'])
            mock_response.status_code = 200
            mock_response.text = "OK"
            mock_response.headers = {}
            
            # Mock all HTTP methods to return the mock_response
            async def mock_http_method(*args, **kwargs):
                return mock_response
            
            mock_client.get = mock_http_method
            mock_client.post = mock_http_method
            mock_client.put = mock_http_method
            mock_client.delete = mock_http_method
            mock_client.patch = mock_http_method
            mock_client.head = mock_http_method
            mock_client.options = mock_http_method
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Test with skip_auth_endpoints=True
            results = await tester.test_multiple_endpoints(
                endpoints,
                skip_auth_endpoints=True
            )
            
            # Should have 1 SUCCESS (health) and 2 SKIPPED (auth required)
            assert len(results) == 3
            success_results = [r for r in results if r.status == TestStatus.SUCCESS]
            skipped_results = [r for r in results if r.status == TestStatus.SKIPPED]
            
            assert len(success_results) == 1
            assert len(skipped_results) == 2
            assert success_results[0].endpoint.path == "/health"


class TestVerboseLogging:
    """Test verbose logging functionality"""
    
    def test_verbose_parameter_in_endpoint_tester(self):
        """Test that EndpointTester accepts verbose parameter"""
        tester = EndpointTester(
            base_url="https://test.com",
            verbose=True,
        )
        
        assert tester.verbose is True
    
    @pytest.mark.asyncio
    async def test_verbose_logging_output(self, caplog):
        """Test that verbose mode logs additional request/response details"""
        import logging
        caplog.set_level(logging.INFO)
        
        tester = EndpointTester(
            base_url="https://test.com",
            verbose=True,
        )
        
        endpoint = Endpoint(method="GET", path="/api/test", requires_auth=False)
        
        # Mock HTTP client
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock(spec=['status_code', 'text', 'headers'])
            mock_response.status_code = 200
            mock_response.text = "Test response body"
            mock_response.headers = {"Content-Type": "application/json"}
            
            # Mock all HTTP methods to return the mock_response
            async def mock_http_method(*args, **kwargs):
                return mock_response
            
            mock_client.get = mock_http_method
            mock_client.post = mock_http_method
            mock_client.put = mock_http_method
            mock_client.delete = mock_http_method
            mock_client.patch = mock_http_method
            mock_client.head = mock_http_method
            mock_client.options = mock_http_method
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Test with verbose logging
            await tester.test_endpoint(endpoint)
            
            # Verify verbose logs contain request/response details
            log_text = caplog.text
            assert "Request timeout:" in log_text
            assert "Expected status codes:" in log_text
            assert "Response headers:" in log_text
            assert "Response body preview:" in log_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Unit tests for EndpointDiscoverer module

Tests endpoint discovery from various frameworks (ASP.NET, Express, FastAPI)
and OpenAPI specifications.
"""

import pytest
from pathlib import Path
import tempfile
import yaml
import json

from specify_cli.validation.endpoint_discoverer import EndpointDiscoverer, Endpoint


class TestEndpointDiscoverer:
    """Test EndpointDiscoverer class"""
    
    def test_initialization(self, tmp_path):
        """Test discoverer initialization"""
        discoverer = EndpointDiscoverer(tmp_path)
        
        assert discoverer.project_root == tmp_path
        assert discoverer.endpoints == []
    
    def test_parse_openapi_yaml(self, tmp_path):
        """Test parsing OpenAPI YAML specification"""
        # Create OpenAPI spec
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/api/users": {
                    "get": {
                        "summary": "Get users",
                        "security": [{"bearerAuth": []}]
                    },
                    "post": {
                        "summary": "Create user"
                    }
                },
                "/api/health": {
                    "get": {
                        "summary": "Health check"
                    }
                }
            }
        }
        
        spec_file = tmp_path / "openapi.yaml"
        with open(spec_file, 'w') as f:
            yaml.dump(openapi_spec, f)
        
        # Parse spec
        discoverer = EndpointDiscoverer(tmp_path)
        endpoints = discoverer.parse_openapi_spec(spec_file)
        
        assert len(endpoints) == 3
        
        # Check GET /api/users (authenticated)
        get_users = next(e for e in endpoints if e.method == "GET" and e.path == "/api/users")
        assert get_users.requires_auth == True
        assert get_users.description == "Get users"
        
        # Check POST /api/users (no auth)
        post_users = next(e for e in endpoints if e.method == "POST" and e.path == "/api/users")
        assert post_users.requires_auth == False
        assert post_users.description == "Create user"
        
        # Check GET /api/health
        health = next(e for e in endpoints if e.path == "/api/health")
        assert health.method == "GET"
        assert health.requires_auth == False
    
    def test_parse_openapi_json(self, tmp_path):
        """Test parsing OpenAPI JSON specification"""
        openapi_spec = {
            "openapi": "3.0.0",
            "paths": {
                "/api/status": {
                    "get": {
                        "summary": "Get status"
                    }
                }
            }
        }
        
        spec_file = tmp_path / "swagger.json"
        with open(spec_file, 'w') as f:
            json.dump(openapi_spec, f)
        
        discoverer = EndpointDiscoverer(tmp_path)
        endpoints = discoverer.parse_openapi_spec(spec_file)
        
        assert len(endpoints) == 1
        assert endpoints[0].method == "GET"
        assert endpoints[0].path == "/api/status"
    
    def test_discover_aspnet_controller(self, tmp_path):
        """Test discovering endpoints from ASP.NET controller"""
        controller_code = """
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;

namespace MyApp.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class UsersController : ControllerBase
    {
        [HttpGet]
        public IActionResult GetAll()
        {
            return Ok();
        }
        
        [HttpGet("{id}")]
        [Authorize]
        public IActionResult GetById(int id)
        {
            return Ok();
        }
        
        [HttpPost]
        [Authorize(Roles = "Admin")]
        public IActionResult Create()
        {
            return Ok();
        }
        
        [HttpPut("{id}")]
        public IActionResult Update(int id)
        {
            return Ok();
        }
        
        [HttpDelete("{id}")]
        public IActionResult Delete(int id)
        {
            return Ok();
        }
    }
}
"""
        
        controller_file = tmp_path / "UsersController.cs"
        controller_file.write_text(controller_code)
        
        discoverer = EndpointDiscoverer(tmp_path)
        endpoints = discoverer.discover_endpoints()
        
        assert len(endpoints) >= 5
        
        # Check methods are detected
        methods = {e.method for e in endpoints}
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods
        
        # Check authentication is detected
        auth_endpoints = [e for e in endpoints if e.requires_auth]
        assert len(auth_endpoints) >= 2  # GetById and Create have [Authorize]
    
    def test_discover_aspnet_minimal_api(self, tmp_path):
        """Test discovering endpoints from ASP.NET minimal API"""
        program_code = """
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/", () => "Hello World!");

app.MapGet("/api/users", () => new List<User>())
    .RequireAuthorization();

app.MapPost("/api/users", (User user) => Results.Created($"/api/users/{user.Id}", user));

app.MapGet("/api/health", () => Results.Ok());

app.Run();
"""
        
        program_file = tmp_path / "Program.cs"
        program_file.write_text(program_code)
        
        discoverer = EndpointDiscoverer(tmp_path)
        endpoints = discoverer.discover_endpoints()
        
        assert len(endpoints) >= 4
        
        # Check root endpoint
        root = next((e for e in endpoints if e.path == "/" and e.method == "GET"), None)
        assert root is not None
        
        # Check authenticated endpoint
        users_get = next((e for e in endpoints if e.path == "/api/users" and e.method == "GET"), None)
        assert users_get is not None
        assert users_get.requires_auth == True
    
    def test_discover_express_routes(self, tmp_path):
        """Test discovering endpoints from Express.js application"""
        server_code = """
const express = require('express');
const app = express();

const requireAuth = (req, res, next) => next();

app.get('/', (req, res) => {
  res.send('Hello World');
});

app.get('/api/users', requireAuth, (req, res) => {
  res.json({ users: [] });
});

app.post('/api/users', (req, res) => {
  res.status(201).json({});
});

app.put('/api/users/:id', (req, res) => {
  res.json({});
});

app.delete('/api/users/:id', requireAuth, (req, res) => {
  res.status(204).send();
});

app.route('/api/products')
  .get((req, res) => res.json({}))
  .post((req, res) => res.json({}));

app.listen(3000);
"""
        
        server_file = tmp_path / "server.js"
        server_file.write_text(server_code)
        
        discoverer = EndpointDiscoverer(tmp_path)
        endpoints = discoverer.discover_endpoints()
        
        assert len(endpoints) >= 6
        
        # Check methods
        methods = {e.method for e in endpoints}
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods
        
        # Check auth detection
        auth_endpoints = [e for e in endpoints if e.requires_auth]
        assert len(auth_endpoints) >= 2  # requireAuth middleware detected
    
    def test_discover_fastapi_endpoints(self, tmp_path):
        """Test discovering endpoints from FastAPI application"""
        main_code = """
from fastapi import FastAPI, Depends
from typing import List

app = FastAPI()

def get_current_user():
    return {"user": "test"}

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/api/users")
def get_users(current_user = Depends(get_current_user)):
    return []

@app.post("/api/users")
def create_user():
    return {"id": 1}

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.put("/api/users/{user_id}")
def update_user(user_id: int, current_user = Depends(get_current_user)):
    return {"id": user_id}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    return {"deleted": True}
"""
        
        main_file = tmp_path / "main.py"
        main_file.write_text(main_code)
        
        discoverer = EndpointDiscoverer(tmp_path)
        endpoints = discoverer.discover_endpoints()
        
        assert len(endpoints) >= 6
        
        # Check methods
        methods = {e.method for e in endpoints}
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods
        
        # Check auth detection (Depends(get_current_user))
        auth_endpoints = [e for e in endpoints if e.requires_auth]
        assert len(auth_endpoints) >= 2  # get_users and update_user use Depends
    
    def test_deduplicate_endpoints(self, tmp_path):
        """Test that duplicate endpoints are removed"""
        # Create multiple files with same endpoints
        file1 = tmp_path / "routes1.py"
        file1.write_text("""
@app.get("/api/users")
def get_users():
    pass
""")
        
        file2 = tmp_path / "routes2.py"
        file2.write_text("""
@app.get("/api/users")
def get_users_v2():
    pass
""")
        
        discoverer = EndpointDiscoverer(tmp_path)
        endpoints = discoverer.discover_endpoints()
        
        # Should only have one GET /api/users
        users_endpoints = [e for e in endpoints if e.method == "GET" and e.path == "/api/users"]
        assert len(users_endpoints) == 1
    
    def test_get_endpoints_by_method(self, tmp_path):
        """Test filtering endpoints by HTTP method"""
        openapi_spec = {
            "openapi": "3.0.0",
            "paths": {
                "/api/users": {
                    "get": {},
                    "post": {}
                },
                "/api/products": {
                    "get": {},
                    "delete": {}
                }
            }
        }
        
        spec_file = tmp_path / "openapi.yaml"
        with open(spec_file, 'w') as f:
            yaml.dump(openapi_spec, f)
        
        discoverer = EndpointDiscoverer(tmp_path)
        discoverer.discover_endpoints()
        
        get_endpoints = discoverer.get_endpoints_by_method("GET")
        assert len(get_endpoints) == 2
        
        post_endpoints = discoverer.get_endpoints_by_method("POST")
        assert len(post_endpoints) == 1
        
        delete_endpoints = discoverer.get_endpoints_by_method("DELETE")
        assert len(delete_endpoints) == 1
    
    def test_get_authenticated_endpoints(self, tmp_path):
        """Test filtering authenticated endpoints"""
        openapi_spec = {
            "openapi": "3.0.0",
            "paths": {
                "/api/public": {
                    "get": {}
                },
                "/api/private": {
                    "get": {
                        "security": [{"bearerAuth": []}]
                    }
                },
                "/api/admin": {
                    "post": {
                        "security": [{"apiKey": []}]
                    }
                }
            }
        }
        
        spec_file = tmp_path / "openapi.yaml"
        with open(spec_file, 'w') as f:
            yaml.dump(openapi_spec, f)
        
        discoverer = EndpointDiscoverer(tmp_path)
        discoverer.discover_endpoints()
        
        auth_endpoints = discoverer.get_authenticated_endpoints()
        assert len(auth_endpoints) == 2
        
        public_endpoints = discoverer.get_public_endpoints()
        assert len(public_endpoints) == 1
    
    def test_empty_project(self, tmp_path):
        """Test discovering endpoints in empty project"""
        discoverer = EndpointDiscoverer(tmp_path)
        endpoints = discoverer.discover_endpoints()
        
        assert len(endpoints) == 0
    
    def test_endpoint_string_representation(self):
        """Test Endpoint __str__ method"""
        endpoint = Endpoint(
            method="GET",
            path="/api/users",
            requires_auth=True,
        )
        
        assert "GET" in str(endpoint)
        assert "/api/users" in str(endpoint)
        assert "[AUTH]" in str(endpoint)
    
    def test_endpoint_to_dict(self):
        """Test Endpoint to_dict method"""
        endpoint = Endpoint(
            method="POST",
            path="/api/products",
            requires_auth=False,
            source_file="routes.py",
            line_number=42,
            description="Create a product",
        )
        
        result = endpoint.to_dict()
        
        assert result["method"] == "POST"
        assert result["path"] == "/api/products"
        assert result["requires_auth"] == False
        assert result["source_file"] == "routes.py"
        assert result["line_number"] == 42
        assert result["description"] == "Create a product"

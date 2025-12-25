"""
API Documentation and Swagger Integration for StockLeague

Provides comprehensive API documentation using Flask-RESTX with:
- Auto-generated Swagger UI
- OpenAPI 3.0 specification
- Request/response examples
- Authentication documentation
- Error code documentation
- Rate limiting information
"""

import logging
from typing import Dict, Any, List
from functools import wraps

logger = logging.getLogger(__name__)


class APIDocumentation:
    """Manages API documentation and Swagger configuration."""
    
    def __init__(self, app=None):
        """Initialize API documentation."""
        self.app = app
        self.endpoints_documented = []
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app."""
        self.app = app
        self._setup_swagger_ui()
    
    def _setup_swagger_ui(self):
        """Setup Swagger UI in the app."""
        if not self.app:
            return
        
        # Add Swagger UI route
        @self.app.route('/api/docs')
        def swagger_ui():
            """Serve Swagger UI."""
            return self._render_swagger_ui()
        
        # Add OpenAPI spec route
        @self.app.route('/api/openapi.json')
        def openapi_spec():
            """Serve OpenAPI specification."""
            from flask import jsonify
            return jsonify(self.get_openapi_spec())
    
    def _render_swagger_ui(self) -> str:
        """Render Swagger UI HTML."""
        return """
        <!DOCTYPE html>
        <html>
          <head>
            <title>StockLeague API Documentation</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.18.3/swagger-ui.min.css">
            <style>
              html{
                box-sizing: border-box;
                overflow: -moz-scrollbars-vertical;
                overflow-y: scroll;
              }
              *,
              *:before,
              *:after{
                box-sizing: inherit;
              }
              body{
                margin:0;
                background: #fafafa;
              }
              .topbar {
                background-color: #1e3a8a;
                padding: 10px 0;
                text-align: center;
              }
              .topbar h1 {
                color: white;
                margin: 0;
              }
            </style>
          </head>
          <body>
            <div class="topbar">
              <h1>📈 StockLeague API Documentation</h1>
            </div>
            <div id="swagger-ui"></div>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.18.3/swagger-ui.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.18.3/swagger-ui-bundle.min.js"></script>
            <script>
            window.onload = function() {
              const ui = SwaggerUIBundle({
                url: "/api/openapi.json",
                dom_id: '#swagger-ui',
                presets: [
                  SwaggerUIBundle.presets.apis,
                  SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout",
                deepLinking: true,
                requestInterceptor: (request) => {
                  // Add authentication token if available
                  const token = localStorage.getItem('api_token');
                  if (token) {
                    request.headers['Authorization'] = 'Bearer ' + token;
                  }
                  return request;
                }
              })
              window.ui = ui
            }
            </script>
          </body>
        </html>
        """
    
    def get_openapi_spec(self) -> Dict[str, Any]:
        """Generate OpenAPI 3.0 specification."""
        return {
            "openapi": "3.0.0",
            "info": {
                "title": "StockLeague API",
                "version": "1.0.0",
                "description": "Comprehensive REST API for StockLeague trading platform",
                "contact": {
                    "name": "StockLeague Support",
                    "url": "https://stockleague.app/support"
                },
                "license": {
                    "name": "MIT"
                }
            },
            "servers": [
                {
                    "url": "https://stockleague.app/api",
                    "description": "Production API"
                },
                {
                    "url": "http://localhost:5000/api",
                    "description": "Development API"
                }
            ],
            "components": self._get_components(),
            "paths": self._get_paths(),
            "tags": self._get_tags(),
            "x-api-key": "Your API key here"
        }
    
    def _get_components(self) -> Dict[str, Any]:
        """Get OpenAPI components (schemas, security, etc)."""
        return {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "JWT authentication token"
                },
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "API key for authentication"
                }
            },
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "username": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                        "cash": {"type": "number", "format": "float"},
                        "created_at": {"type": "string", "format": "date-time"}
                    }
                },
                "League": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "mode": {"type": "string", "enum": ["absolute_value", "percent_change", "gains_only"]},
                        "starting_cash": {"type": "number", "format": "float"},
                        "member_count": {"type": "integer"},
                        "created_at": {"type": "string", "format": "date-time"}
                    }
                },
                "Portfolio": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "integer"},
                        "league_id": {"type": "integer"},
                        "cash": {"type": "number", "format": "float"},
                        "total_value": {"type": "number", "format": "float"},
                        "positions": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Position"}
                        }
                    }
                },
                "Position": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "shares": {"type": "number"},
                        "average_price": {"type": "number", "format": "float"},
                        "current_price": {"type": "number", "format": "float"},
                        "value": {"type": "number", "format": "float"},
                        "gain_loss": {"type": "number", "format": "float"},
                        "gain_loss_percent": {"type": "number", "format": "float"}
                    }
                },
                "Trade": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "user_id": {"type": "integer"},
                        "league_id": {"type": "integer"},
                        "symbol": {"type": "string"},
                        "action": {"type": "string", "enum": ["BUY", "SELL"]},
                        "shares": {"type": "number"},
                        "price": {"type": "number", "format": "float"},
                        "total": {"type": "number", "format": "float"},
                        "timestamp": {"type": "string", "format": "date-time"}
                    }
                },
                "Error": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "message": {"type": "string"},
                        "details": {"type": "object"}
                    }
                }
            }
        }
    
    def _get_paths(self) -> Dict[str, Any]:
        """Get OpenAPI paths for all endpoints."""
        return {
            "/auth/register": {
                "post": {
                    "summary": "Register new user",
                    "tags": ["Authentication"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "username": {"type": "string"},
                                        "email": {"type": "string", "format": "email"},
                                        "password": {"type": "string", "format": "password"}
                                    },
                                    "required": ["username", "email", "password"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "User registered successfully",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            }
                        },
                        "400": {"description": "Invalid input"}
                    }
                }
            },
            "/auth/login": {
                "post": {
                    "summary": "Login user",
                    "tags": ["Authentication"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "username": {"type": "string"},
                                        "password": {"type": "string", "format": "password"}
                                    },
                                    "required": ["username", "password"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Login successful"},
                        "401": {"description": "Invalid credentials"}
                    }
                }
            },
            "/leagues": {
                "get": {
                    "summary": "Get all leagues",
                    "tags": ["Leagues"],
                    "security": [{"BearerAuth": []}],
                    "parameters": [
                        {
                            "name": "page",
                            "in": "query",
                            "schema": {"type": "integer"},
                            "description": "Page number"
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {"type": "integer"},
                            "description": "Items per page"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "List of leagues",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/League"}
                                    }
                                }
                            }
                        }
                    }
                },
                "post": {
                    "summary": "Create new league",
                    "tags": ["Leagues"],
                    "security": [{"BearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string"},
                                        "mode": {"type": "string", "enum": ["absolute_value", "percent_change", "gains_only"]},
                                        "starting_cash": {"type": "number"}
                                    },
                                    "required": ["name", "mode"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "League created",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/League"}
                                }
                            }
                        }
                    }
                }
            },
            "/leagues/{league_id}": {
                "get": {
                    "summary": "Get league details",
                    "tags": ["Leagues"],
                    "parameters": [
                        {
                            "name": "league_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "League details",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/League"}
                                }
                            }
                        },
                        "404": {"description": "League not found"}
                    }
                }
            },
            "/portfolio/{user_id}/{league_id}": {
                "get": {
                    "summary": "Get user portfolio",
                    "tags": ["Portfolio"],
                    "security": [{"BearerAuth": []}],
                    "parameters": [
                        {"name": "user_id", "in": "path", "required": True, "schema": {"type": "integer"}},
                        {"name": "league_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Portfolio details",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Portfolio"}
                                }
                            }
                        }
                    }
                }
            },
            "/trades": {
                "post": {
                    "summary": "Execute trade",
                    "tags": ["Trading"],
                    "security": [{"BearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "league_id": {"type": "integer"},
                                        "symbol": {"type": "string"},
                                        "action": {"type": "string", "enum": ["BUY", "SELL"]},
                                        "shares": {"type": "number"}
                                    },
                                    "required": ["league_id", "symbol", "action", "shares"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Trade executed",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Trade"}
                                }
                            }
                        },
                        "400": {"description": "Invalid trade"}
                    }
                }
            },
            "/analytics/{user_id}/{league_id}": {
                "get": {
                    "summary": "Get portfolio analytics",
                    "tags": ["Analytics"],
                    "security": [{"BearerAuth": []}],
                    "parameters": [
                        {"name": "user_id", "in": "path", "required": True, "schema": {"type": "integer"}},
                        {"name": "league_id", "in": "path", "required": True, "schema": {"type": "integer"}},
                        {"name": "period_days", "in": "query", "schema": {"type": "integer", "default": 30}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Analytics data",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "performance": {"type": "object"},
                                            "risk": {"type": "object"},
                                            "attribution": {"type": "object"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    
    def _get_tags(self) -> List[Dict[str, Any]]:
        """Get API tags for organizing endpoints."""
        return [
            {
                "name": "Authentication",
                "description": "User authentication and authorization endpoints"
            },
            {
                "name": "Leagues",
                "description": "League management endpoints"
            },
            {
                "name": "Portfolio",
                "description": "User portfolio endpoints"
            },
            {
                "name": "Trading",
                "description": "Trading execution endpoints"
            },
            {
                "name": "Analytics",
                "description": "Portfolio analytics and reporting"
            },
            {
                "name": "Admin",
                "description": "Administrative endpoints"
            }
        ]


class APIErrorCodes:
    """API error code documentation."""
    
    CODES = {
        # Authentication errors
        "AUTH_001": {
            "message": "Invalid credentials",
            "status_code": 401,
            "description": "Username or password is incorrect"
        },
        "AUTH_002": {
            "message": "Token expired",
            "status_code": 401,
            "description": "Authentication token has expired"
        },
        "AUTH_003": {
            "message": "Invalid token",
            "status_code": 401,
            "description": "Authentication token is invalid"
        },
        
        # Validation errors
        "VAL_001": {
            "message": "Invalid input",
            "status_code": 400,
            "description": "Request body contains invalid data"
        },
        "VAL_002": {
            "message": "Missing required field",
            "status_code": 400,
            "description": "Required field is missing from request"
        },
        "VAL_003": {
            "message": "Invalid symbol",
            "status_code": 400,
            "description": "Stock symbol is invalid or not supported"
        },
        
        # Trading errors
        "TRADE_001": {
            "message": "Insufficient cash",
            "status_code": 400,
            "description": "Portfolio does not have enough cash for this trade"
        },
        "TRADE_002": {
            "message": "Insufficient shares",
            "status_code": 400,
            "description": "Portfolio does not have enough shares to sell"
        },
        "TRADE_003": {
            "message": "Rate limit exceeded",
            "status_code": 429,
            "description": "Too many trades in short period"
        },
        "TRADE_004": {
            "message": "Market closed",
            "status_code": 400,
            "description": "Trading is not allowed outside market hours"
        },
        
        # Resource errors
        "RES_001": {
            "message": "Not found",
            "status_code": 404,
            "description": "Requested resource does not exist"
        },
        "RES_002": {
            "message": "Permission denied",
            "status_code": 403,
            "description": "User does not have permission to access this resource"
        },
        
        # Server errors
        "SRV_001": {
            "message": "Internal error",
            "status_code": 500,
            "description": "An unexpected server error occurred"
        },
        "SRV_002": {
            "message": "Database error",
            "status_code": 500,
            "description": "Database operation failed"
        }
    }
    
    @classmethod
    def get_code(cls, code: str) -> Dict[str, Any]:
        """Get error code details."""
        return cls.CODES.get(code, {
            "message": "Unknown error",
            "status_code": 500,
            "description": "An unknown error occurred"
        })
    
    @classmethod
    def get_all(cls) -> Dict[str, Dict[str, Any]]:
        """Get all error codes."""
        return cls.CODES


class RateLimitDocumentation:
    """Documents rate limiting policy."""
    
    LIMITS = {
        "trades": {
            "limit": 100,
            "window": "1 hour",
            "description": "Maximum trades per hour per user"
        },
        "api_calls": {
            "limit": 1000,
            "window": "1 hour",
            "description": "Maximum API calls per hour per user"
        },
        "login": {
            "limit": 10,
            "window": "15 minutes",
            "description": "Maximum login attempts"
        },
        "password_reset": {
            "limit": 3,
            "window": "1 hour",
            "description": "Maximum password reset requests"
        }
    }
    
    @staticmethod
    def get_documentation() -> Dict[str, Any]:
        """Get rate limiting documentation."""
        return {
            "title": "Rate Limiting",
            "description": "StockLeague API implements rate limiting to ensure fair usage",
            "headers": {
                "X-RateLimit-Limit": "Maximum requests allowed in window",
                "X-RateLimit-Remaining": "Remaining requests in current window",
                "X-RateLimit-Reset": "Unix timestamp when limit resets"
            },
            "limits": RateLimitDocumentation.LIMITS,
            "error_handling": {
                "status_code": 429,
                "message": "Too Many Requests",
                "retry_after": "Number of seconds to wait before retrying"
            }
        }


def api_doc(summary: str = "", description: str = "", 
            tags: List[str] = None, responses: Dict = None):
    """Decorator to document API endpoints.
    
    Usage:
        @app.route('/api/users/<int:user_id>')
        @api_doc(
            summary="Get user by ID",
            description="Retrieve a specific user's information",
            tags=["Users"],
            responses={
                200: "User found",
                404: "User not found"
            }
        )
        def get_user(user_id):
            ...
    """
    def decorator(f):
        f._api_doc = {
            "summary": summary,
            "description": description,
            "tags": tags or [],
            "responses": responses or {}
        }
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        decorated_function._api_doc = f._api_doc
        return decorated_function
    return decorator

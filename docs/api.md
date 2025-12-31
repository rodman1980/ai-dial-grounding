---
title: API Reference
description: Comprehensive API documentation for User Service endpoints and UserClient methods
version: 1.0.0
last_updated: 2025-12-31
related: [architecture.md, setup.md]
tags: [api, user-service, client, rest]
---

# API Reference

## Table of Contents

- [Overview](#overview)
- [User Service REST API](#user-service-rest-api)
- [UserClient Python API](#userclient-python-api)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Examples](#examples)

## Overview

The AI Grounding project interacts with two primary APIs:

1. **User Service REST API**: Dockerized mock service providing user data
2. **UserClient Python API**: Wrapper client for convenient access from Python code

### Quick Links

- **Swagger UI**: http://localhost:8041/docs
- **ReDoc**: http://localhost:8041/redoc
- **Health Check**: http://localhost:8041/health
- **Source Code**: [task/user_client.py](../task/user_client.py)

## User Service REST API

### Base Configuration

```python
# From task/_constants.py
USER_SERVICE_ENDPOINT = "http://localhost:8041"
```

### Authentication

Currently, the User Service does not require authentication. All endpoints are publicly accessible.

> **Note**: In production scenarios, implement proper authentication (API keys, OAuth, etc.).

---

### GET /v1/users

Retrieve all users from the database.

#### Request

```http
GET /v1/users HTTP/1.1
Host: localhost:8041
Content-Type: application/json
```

#### Response

**Status Code**: `200 OK`

```json
[
  {
    "id": 1,
    "name": "John",
    "surname": "Doe",
    "email": "john.doe@example.com",
    "gender": "male",
    "about": "Passionate about hiking and photography."
  },
  {
    "id": 2,
    "name": "Jane",
    "surname": "Smith",
    "email": "jane.smith@example.com",
    "gender": "female",
    "about": "Loves cooking, traveling, and yoga."
  }
  // ... more users (1000 total by default)
]
```

#### Performance Notes

- **Response Size**: ~500KB-1MB for 1000 users
- **Latency**: ~100-500ms (local Docker)
- **Pagination**: Not implemented (all users returned)

---

### GET /v1/users/{id}

Retrieve a specific user by ID.

#### Request

```http
GET /v1/users/42 HTTP/1.1
Host: localhost:8041
Content-Type: application/json
```

**Path Parameters**:
- `id` (integer, required): User ID

#### Response

**Status Code**: `200 OK`

```json
{
  "id": 42,
  "name": "Alice",
  "surname": "Johnson",
  "email": "alice.j@example.com",
  "gender": "female",
  "about": "Interested in AI, machine learning, and data science."
}
```

**Status Code**: `404 Not Found` (if user doesn't exist)

```json
{
  "detail": "User not found"
}
```

---

### GET /v1/users/search

Search users by specific fields.

#### Request

```http
GET /v1/users/search?name=John&gender=male HTTP/1.1
Host: localhost:8041
Content-Type: application/json
```

**Query Parameters** (all optional, at least one required):
- `name` (string): Filter by first name (case-sensitive)
- `surname` (string): Filter by last name (case-sensitive)
- `email` (string): Filter by email (case-sensitive)
- `gender` (string): Filter by gender (`male` or `female`)

#### Matching Behavior

- **Exact Match**: All provided parameters must match exactly
- **AND Logic**: Multiple parameters are combined with AND (not OR)
- **Case Sensitivity**: Searches are case-sensitive
- **No Wildcards**: Partial matching not supported (e.g., "Joh" won't match "John")

#### Response

**Status Code**: `200 OK`

```json
[
  {
    "id": 1,
    "name": "John",
    "surname": "Doe",
    "email": "john.doe@example.com",
    "gender": "male",
    "about": "Passionate about hiking and photography."
  },
  {
    "id": 15,
    "name": "John",
    "surname": "Smith",
    "email": "john.smith@example.com",
    "gender": "male",
    "about": "Enjoys reading and chess."
  }
]
```

**Empty Results**: Returns `[]` if no matches found.

#### Example Queries

```bash
# Find all users named "John"
curl "http://localhost:8041/v1/users/search?name=John"

# Find users with surname "Smith"
curl "http://localhost:8041/v1/users/search?surname=Smith"

# Find female users named "Alice"
curl "http://localhost:8041/v1/users/search?name=Alice&gender=female"

# Find user by email
curl "http://localhost:8041/v1/users/search?email=john.doe@example.com"
```

---

### GET /health

Health check endpoint for service monitoring.

#### Request

```http
GET /health HTTP/1.1
Host: localhost:8041
Content-Type: application/json
```

#### Response

**Status Code**: `200 OK`

```json
{
  "status": "healthy",
  "service": "UserService",
  "version": "1.0.0",
  "timestamp": "2025-12-31T12:00:00Z"
}
```

**Status Code**: `503 Service Unavailable` (if service unhealthy)

---

## UserClient Python API

Python wrapper for convenient access to the User Service API.

### Class: UserClient

Located in [task/user_client.py](../task/user_client.py).

```python
from task.user_client import UserClient

client = UserClient()
```

---

### Method: get_all_users()

Retrieve all users from the service.

```python
def get_all_users(self) -> list[dict[str, Any]]:
    """
    Fetch all users from the User Service.
    
    Returns:
        list[dict]: List of user dictionaries
        
    Raises:
        Exception: If HTTP request fails or returns non-200 status
        
    Example:
        >>> client = UserClient()
        >>> users = client.get_all_users()
        Get 1000 users successfully
        >>> len(users)
        1000
    """
```

**Output Example**:
```
Get 1000 users successfully
```

**Usage**:
```python
client = UserClient()
users = client.get_all_users()
print(f"Retrieved {len(users)} users")
for user in users[:3]:
    print(f"- {user['name']} {user['surname']}")
```

---

### Method: get_user()

Retrieve a specific user by ID.

```python
async def get_user(self, id: int) -> dict[str, Any]:
    """
    Fetch a single user by ID.
    
    Args:
        id (int): User ID to retrieve
        
    Returns:
        dict: User data dictionary
        
    Raises:
        Exception: If user not found or HTTP request fails
        
    Example:
        >>> client = UserClient()
        >>> user = await client.get_user(42)
        >>> user['name']
        'Alice'
    """
```

> **Note**: This method is async but uses synchronous `requests.get()` internally. Consider refactoring for true async I/O.

**Usage**:
```python
import asyncio
from task.user_client import UserClient

async def main():
    client = UserClient()
    user = await client.get_user(42)
    print(f"Found: {user['name']} {user['surname']}")

asyncio.run(main())
```

---

### Method: search_users()

Search users by specific fields.

```python
def search_users(
    self,
    name: Optional[str] = None,
    surname: Optional[str] = None,
    email: Optional[str] = None,
    gender: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Search users by optional fields. Only non-None parameters are included.
    
    Args:
        name (str, optional): Filter by first name
        surname (str, optional): Filter by last name
        email (str, optional): Filter by email address
        gender (str, optional): Filter by gender ("male" or "female")
        
    Returns:
        list[dict]: List of matching user dictionaries
        
    Raises:
        Exception: If HTTP request fails
        
    Example:
        >>> client = UserClient()
        >>> users = client.search_users(name="John", gender="male")
        Get 5 users successfully
        >>> len(users)
        5
    """
```

**Output Example**:
```
Get 5 users successfully
```

**Usage**:
```python
client = UserClient()

# Search by name only
johns = client.search_users(name="John")

# Search by multiple fields
female_smiths = client.search_users(surname="Smith", gender="female")

# Search by email
user = client.search_users(email="alice.j@example.com")
```

---

### Method: health()

Check User Service health.

```python
def health(self) -> dict[str, Any]:
    """
    Check User Service health status.
    
    Returns:
        dict: Health check response data
        
    Raises:
        Exception: If service is unhealthy or unreachable
        
    Example:
        >>> client = UserClient()
        >>> status = client.health()
        >>> status['status']
        'healthy'
    """
```

**Usage**:
```python
client = UserClient()
try:
    health = client.health()
    print(f"Service status: {health['status']}")
except Exception as e:
    print(f"Service unavailable: {e}")
```

---

## Data Models

### User Record

Standard user object returned by all endpoints.

```python
from typing import TypedDict

class User(TypedDict):
    id: int
    name: str
    surname: str
    email: str
    gender: str  # "male" or "female"
    about: str
```

**Field Descriptions**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | int | Unique user identifier | `42` |
| `name` | str | First name | `"Alice"` |
| `surname` | str | Last name | `"Johnson"` |
| `email` | str | Email address | `"alice.j@example.com"` |
| `gender` | str | Gender (`"male"` or `"female"`) | `"female"` |
| `about` | str | Biography/interests | `"Loves hiking and photography"` |

**Sample User**:
```json
{
  "id": 123,
  "name": "Emma",
  "surname": "Wilson",
  "email": "emma.w@example.com",
  "gender": "female",
  "about": "Passionate about AI, machine learning, and data visualization. Enjoys hiking and landscape photography on weekends."
}
```

### Health Response

```python
class HealthResponse(TypedDict):
    status: str
    service: str
    version: str
    timestamp: str
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | When It Occurs |
|------|---------|----------------|
| 200 | OK | Request successful |
| 404 | Not Found | User ID doesn't exist |
| 422 | Unprocessable Entity | Invalid query parameters |
| 500 | Internal Server Error | Service error |
| 503 | Service Unavailable | Service down or unhealthy |

### Exception Handling in UserClient

All UserClient methods raise `Exception` on HTTP errors:

```python
try:
    users = client.get_all_users()
except Exception as e:
    print(f"Error: {e}")
    # Example: "HTTP 503: Service unavailable"
```

**Best Practices**:

1. **Always wrap API calls in try-except blocks**
```python
from task.user_client import UserClient

def safe_get_users():
    client = UserClient()
    try:
        return client.get_all_users()
    except Exception as e:
        print(f"Failed to fetch users: {e}")
        return []
```

2. **Check health before bulk operations**
```python
client = UserClient()
try:
    client.health()
    users = client.get_all_users()
except Exception as e:
    print(f"Service check failed: {e}")
```

3. **Handle missing users gracefully**
```python
async def get_user_safe(client, user_id):
    try:
        return await client.get_user(user_id)
    except Exception:
        return None  # User doesn't exist or deleted
```

---

## Examples

### Example 1: Fetch and Filter Users

```python
from task.user_client import UserClient

client = UserClient()

# Get all users
all_users = client.get_all_users()
print(f"Total users: {len(all_users)}")

# Filter in Python
hikers = [u for u in all_users if 'hiking' in u['about'].lower()]
print(f"Users interested in hiking: {len(hikers)}")
```

### Example 2: Search by Multiple Fields

```python
from task.user_client import UserClient

client = UserClient()

# Search for female users named "Emma"
results = client.search_users(name="Emma", gender="female")

for user in results:
    print(f"{user['name']} {user['surname']} - {user['email']}")
```

### Example 3: Fetch Users by ID List

```python
import asyncio
from task.user_client import UserClient

async def fetch_users_by_ids(user_ids: list[int]):
    client = UserClient()
    tasks = [client.get_user(uid) for uid in user_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions (deleted users)
    valid_users = [r for r in results if isinstance(r, dict)]
    return valid_users

# Usage
user_ids = [1, 5, 10, 99999]  # 99999 doesn't exist
users = asyncio.run(fetch_users_by_ids(user_ids))
print(f"Found {len(users)} valid users")
```

### Example 4: Health Check with Retry

```python
import time
from task.user_client import UserClient

def wait_for_service(max_retries=5, delay=2):
    client = UserClient()
    for i in range(max_retries):
        try:
            health = client.health()
            print(f"Service ready: {health['status']}")
            return True
        except Exception as e:
            print(f"Attempt {i+1}/{max_retries} failed: {e}")
            time.sleep(delay)
    return False

# Usage at startup
if wait_for_service():
    print("Starting application...")
else:
    print("Service unavailable, exiting")
```

### Example 5: Batch Processing with Rate Limiting

```python
import asyncio
from task.user_client import UserClient

async def fetch_users_batched(user_ids: list[int], batch_size: int = 10):
    client = UserClient()
    results = []
    
    for i in range(0, len(user_ids), batch_size):
        batch = user_ids[i:i+batch_size]
        print(f"Fetching batch {i//batch_size + 1}...")
        
        tasks = [client.get_user(uid) for uid in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        results.extend([r for r in batch_results if isinstance(r, dict)])
        
        # Rate limiting delay
        await asyncio.sleep(0.1)
    
    return results

# Usage
ids = list(range(1, 101))  # Fetch users 1-100
users = asyncio.run(fetch_users_batched(ids, batch_size=10))
print(f"Successfully fetched {len(users)} users")
```

---

## Integration Patterns

### Pattern 1: Initialization Check

```python
from task.user_client import UserClient

class MyApplication:
    def __init__(self):
        self.client = UserClient()
        self._verify_connection()
    
    def _verify_connection(self):
        try:
            health = self.client.health()
            print(f"Connected to User Service: {health['version']}")
        except Exception as e:
            raise RuntimeError(f"Cannot connect to User Service: {e}")
```

### Pattern 2: Caching Strategy

```python
from functools import lru_cache
from task.user_client import UserClient

class CachedUserClient:
    def __init__(self):
        self.client = UserClient()
    
    @lru_cache(maxsize=1)
    def get_all_users_cached(self):
        """Cache all users for 1 minute"""
        return self.client.get_all_users()
    
    def invalidate_cache(self):
        self.get_all_users_cached.cache_clear()
```

### Pattern 3: Async Context Manager

```python
import asyncio
from task.user_client import UserClient

class AsyncUserClient:
    async def __aenter__(self):
        self.client = UserClient()
        # Verify connection
        await asyncio.to_thread(self.client.health)
        return self.client
    
    async def __aexit__(self, *args):
        pass  # Cleanup if needed

# Usage
async def main():
    async with AsyncUserClient() as client:
        users = await asyncio.to_thread(client.get_all_users)
        print(f"Fetched {len(users)} users")
```

---

## Swagger/OpenAPI Specification

For interactive API exploration, visit the automatically generated Swagger UI:

**URL**: http://localhost:8041/docs

Features:
- Try out API endpoints directly in browser
- View request/response schemas
- Generate code snippets
- Download OpenAPI spec

---

## Related Documentation

- [Architecture](./architecture.md) - Integration patterns and data flows
- [Setup Guide](./setup.md) - Starting the User Service
- [Glossary](./glossary.md) - API terminology

---

## Open Questions

- **Q1**: Should we implement pagination for `/v1/users`?
- **Q2**: What are appropriate rate limits for production?
- **Q3**: Should search support case-insensitive matching?
- **Q4**: Consider adding `/v1/users/bulk` for batch fetching?

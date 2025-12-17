# Authentication Sequence Diagram

**Purpose**: Show the complete authentication flow from user login to authorized API access

**Last Updated**: {{CURRENT_DATE}}

---

## Diagram

```mermaid
sequenceDiagram
    actor User
    participant Frontend as Web App
    participant Backend as API Server
    participant AuthProvider as Auth Provider
    participant Database
    
    Note over User,Database: User initiates login
    
    User->>Frontend: Click "Login"
    Frontend->>AuthProvider: Redirect to OAuth provider
    Note right of Frontend: State & PKCE parameters included
    
    User->>AuthProvider: Enter credentials
    activate AuthProvider
    AuthProvider->>AuthProvider: Validate credentials
    AuthProvider-->>Frontend: Redirect with auth code
    deactivate AuthProvider
    Note right of AuthProvider: Temporary authorization code
    
    Frontend->>Backend: POST /auth/callback<br/>{code, state}
    activate Backend
    
    Backend->>AuthProvider: Exchange code for tokens
    Note right of Backend: Client credentials + code
    activate AuthProvider
    AuthProvider-->>Backend: Access token + ID token + User info
    deactivate AuthProvider
    
    Backend->>Backend: Validate tokens
    Backend->>Database: Query user by email
    activate Database
    
    alt User exists
        Database-->>Backend: User record
        Backend->>Database: Update last_login
    else User doesn't exist
        Database-->>Backend: Not found
        Backend->>Database: Create new user
        Database-->>Backend: New user ID
    end
    
    deactivate Database
    
    Backend->>Backend: Generate JWT<br/>{user_id, roles, exp}
    Backend-->>Frontend: {jwt: "...", user: {...}}
    deactivate Backend
    
    Frontend->>Frontend: Store JWT in localStorage/cookie
    Frontend-->>User: Redirect to dashboard
    
    Note over User,Database: User makes authenticated request
    
    User->>Frontend: Navigate to protected page
    Frontend->>Backend: GET /api/protected<br/>Authorization: Bearer JWT
    activate Backend
    
    Backend->>Backend: Verify JWT signature
    Backend->>Backend: Check expiration
    Backend->>Backend: Extract user_id
    
    Backend->>Database: Fetch user details
    activate Database
    Database-->>Backend: User data
    deactivate Database
    
    Backend-->>Frontend: {data: "..."}
    deactivate Backend
    Frontend-->>User: Display protected content
```

---

## Flow Description

### 1. Login Initiation

User clicks "Login" button and is redirected to the OAuth provider (e.g., Google, GitHub, Auth0).

**Parameters sent**:
- `client_id`: Application identifier
- `redirect_uri`: Callback URL
- `scope`: Requested permissions (e.g., `openid profile email`)
- `state`: CSRF protection token
- `code_challenge`: PKCE parameter (for public clients)

### 2. User Authentication

User authenticates with the OAuth provider using their credentials (username/password, 2FA, etc.).

### 3. Authorization Code Exchange

OAuth provider redirects back to application with:
- `code`: Temporary authorization code (single-use, short-lived)
- `state`: Same state parameter (verify CSRF protection)

Frontend sends code to backend, which exchanges it for tokens:
- **Access Token**: Used to access protected resources
- **ID Token**: Contains user identity information (JWT)
- **Refresh Token** (optional): Used to obtain new access tokens

### 4. User Creation/Update

Backend:
1. Validates tokens (signature, expiration, issuer)
2. Extracts user information from ID token
3. Checks if user exists in database
4. Creates new user or updates existing user's last_login

### 5. Session Token Generation

Backend generates its own JWT containing:
- `user_id`: Internal user identifier
- `roles`: User permissions/roles
- `exp`: Token expiration time
- `iat`: Token issued-at time

This JWT is returned to frontend for subsequent API calls.

### 6. Authenticated Requests

For each protected API request:
1. Frontend includes JWT in `Authorization: Bearer <token>` header
2. Backend verifies JWT signature and expiration
3. Backend extracts user_id and fetches user data if needed
4. Backend authorizes action based on user roles
5. Backend returns protected data

---

## Security Considerations

### Token Storage

**Frontend**:
- **Preferred**: HttpOnly cookie (prevents XSS)
- **Alternative**: localStorage (simpler but vulnerable to XSS)
- Never store tokens in sessionStorage or URL

**Backend**:
- Store refresh tokens securely (encrypted at rest)
- Never log tokens

### Token Lifetime

- **Access tokens**: Short-lived (15 minutes - 1 hour)
- **Refresh tokens**: Long-lived (7-90 days)
- **Session cookies**: Match access token lifetime

### PKCE (Proof Key for Code Exchange)

Required for public clients (SPAs, mobile apps):
- Prevents authorization code interception attacks
- Use code_challenge and code_verifier parameters

### CSRF Protection

- Validate `state` parameter matches
- Use HttpOnly, SameSite cookies
- Implement CSRF tokens for state-changing operations

---

## Error Scenarios

### Authentication Failure

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant AuthProvider
    
    User->>Frontend: Click "Login"
    Frontend->>AuthProvider: Redirect
    User->>AuthProvider: Enter invalid credentials
    AuthProvider-->>Frontend: Redirect with error
    Frontend-->>User: Show "Login failed" message
```

### Expired JWT

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant Backend
    
    User->>Frontend: Make API request
    Frontend->>Backend: GET /api/data<br/>Authorization: Bearer <expired_jwt>
    Backend->>Backend: Verify JWT - EXPIRED
    Backend-->>Frontend: 401 Unauthorized
    Frontend->>Frontend: Clear stored JWT
    Frontend-->>User: Redirect to login
```

### Token Refresh

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant Backend
    
    Note over Frontend: Access token expired
    
    Frontend->>Backend: POST /auth/refresh<br/>{refresh_token}
    Backend->>Backend: Validate refresh token
    Backend->>Backend: Generate new access token
    Backend-->>Frontend: {jwt: "...", expires_in: 3600}
    Frontend->>Frontend: Store new JWT
    Frontend->>Backend: Retry original request
```

---

## Alternative Flows

### Session-Based Authentication

For server-rendered applications:

```mermaid
sequenceDiagram
    actor User
    participant Server
    participant Database
    
    User->>Server: POST /login<br/>{username, password}
    Server->>Database: Query user
    Database-->>Server: User + password_hash
    Server->>Server: Verify password
    Server->>Server: Create session
    Server->>Database: Store session
    Server-->>User: Set-Cookie: session_id=...
    User->>Server: GET /dashboard<br/>Cookie: session_id=...
    Server->>Database: Fetch session
    Database-->>Server: Session data
    Server-->>User: Render dashboard
```

### API Key Authentication

For service-to-service communication:

```mermaid
sequenceDiagram
    participant ServiceA
    participant ServiceB
    participant Database
    
    ServiceA->>ServiceB: GET /api/data<br/>X-API-Key: <key>
    ServiceB->>Database: Validate API key
    Database-->>ServiceB: Key valid, permissions
    ServiceB-->>ServiceA: {data: "..."}
```

---

## Implementation Checklist

- [ ] OAuth client registered with provider
- [ ] Client ID and secret configured (backend only)
- [ ] Redirect URLs whitelisted
- [ ] PKCE implemented (for public clients)
- [ ] State parameter validated
- [ ] Tokens validated (signature, expiration, issuer)
- [ ] User database schema includes auth fields
- [ ] JWT secret configured (strong random value)
- [ ] Token refresh endpoint implemented
- [ ] Logout endpoint implemented (invalidate tokens)
- [ ] Rate limiting on auth endpoints
- [ ] Audit logging for auth events

---

## Related Documentation

- [Authentication ADR](../ADRs/XXX-authentication.md) - Why we chose this approach
- [Security Policy](../SECURITY.md) - Security guidelines
- [API Documentation](../API.md) - API endpoint details

---

**Note**: This is a template. Customize with your specific OAuth provider and authentication flow.

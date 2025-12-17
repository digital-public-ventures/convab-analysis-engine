# Architecture Diagrams

**Purpose**: Visual documentation of system architecture, component relationships, and data flows.

**Why Diagrams**: "A picture is worth a thousand words" - diagrams communicate complex systems quickly and reduce misunderstandings.

---

## Diagram Types in This Directory

| Type                                        | Purpose                                  | Tool                  | Example              |
| ------------------------------------------- | ---------------------------------------- | --------------------- | -------------------- |
| [System Context](#c4-system-context)        | High-level system overview               | Mermaid C4            | `system-context.md`  |
| [Container](#c4-container)                  | Major runtime containers/services        | Mermaid C4            | `container.md`       |
| [Component](#c4-component)                  | Components within a container            | Mermaid C4            | `component.md`       |
| [Sequence](#sequence-diagrams)              | Interactions over time                   | Mermaid/PlantUML      | `sequence-*.md`      |
| [Entity-Relationship](#er-diagrams)         | Database schema                          | Mermaid               | `er-diagram.md`      |
| [State Machine](#state-diagrams)            | State transitions                        | Mermaid               | `state-*.md`         |
| [Data Flow](#data-flow-diagrams)            | How data moves through system            | Mermaid Flowchart     | `dataflow-*.md`      |

---

## Quick Start

### Creating a New Diagram

1. **Choose type**: What are you documenting?
2. **Pick tool**: Mermaid (recommended) or PlantUML
3. **Copy template**: From this README or example files
4. **Edit**: Modify for your use case
5. **Render**: Use GitHub, VS Code, or online renderer
6. **Commit**: Add to git with descriptive filename

### Rendering Diagrams

**GitHub**: Automatically renders Mermaid in `.md` files

**VS Code**: Install "Markdown Preview Mermaid Support" extension

**Online**: 
- Mermaid: https://mermaid.live/
- PlantUML: https://www.plantuml.com/plantuml/

**CLI**:
```bash
# Mermaid CLI
npm install -g @mermaid-js/mermaid-cli
mmdc -i diagram.mmd -o diagram.png

# PlantUML CLI  
java -jar plantuml.jar diagram.puml
```

---

## C4 Model Diagrams

### Overview

The C4 model provides hierarchical views of software architecture:

1. **System Context**: How your system fits in the world
2. **Container**: High-level technology choices
3. **Component**: Logical components within containers
4. **Code**: (Optional) Class diagrams - use sparingly

**Reference**: https://c4model.com/

### C4 System Context

**Shows**: System boundaries, external users, external systems

**Template**:

````markdown
# System Context Diagram

```mermaid
C4Context
    title System Context for cfpb-exploration
    
    Person(user, "User", "End user of the system")
    Person(admin, "Administrator", "System administrator")
    
    System(system, "cfpb-exploration", "Core application")
    
    System_Ext(auth, "Auth Provider", "OAuth2 authentication")
    System_Ext(payment, "Payment Gateway", "Process payments")
    SystemDb_Ext(analytics, "Analytics", "User behavior tracking")
    
    Rel(user, system, "Uses", "HTTPS")
    Rel(admin, system, "Manages", "HTTPS")
    Rel(system, auth, "Authenticates", "OAuth2")
    Rel(system, payment, "Processes payments", "API")
    Rel(system, analytics, "Sends events", "HTTPS")
```
````

**Example**:

```mermaid
C4Context
    title System Context for E-commerce Platform
    
    Person(customer, "Customer", "Browses and purchases products")
    Person(admin, "Admin", "Manages inventory and orders")
    
    System(ecommerce, "E-commerce Platform", "Online shopping system")
    
    System_Ext(stripe, "Stripe", "Payment processing")
    System_Ext(shippo, "Shippo", "Shipping labels and tracking")
    System_Ext(sendgrid, "SendGrid", "Email notifications")
    
    Rel(customer, ecommerce, "Shops", "HTTPS")
    Rel(admin, ecommerce, "Manages", "HTTPS")
    Rel(ecommerce, stripe, "Processes payments", "API")
    Rel(ecommerce, shippo, "Creates shipments", "API")
    Rel(ecommerce, sendgrid, "Sends emails", "SMTP")
```

### C4 Container

**Shows**: High-level technology choices, data storage, communication

**Template**:

````markdown
# Container Diagram

```mermaid
C4Container
    title Container Diagram for cfpb-exploration
    
    Person(user, "User")
    
    Container(web, "Web Application", "React", "SPA")
    Container(api, "API", "Node.js/Express", "REST API")
    Container(worker, "Background Worker", "Python", "Async processing")
    
    ContainerDb(db, "Database", "PostgreSQL", "Stores data")
    ContainerDb(cache, "Cache", "Redis", "Session & caching")
    Container(storage, "File Storage", "S3", "User uploads")
    
    Rel(user, web, "Uses", "HTTPS")
    Rel(web, api, "API calls", "JSON/HTTPS")
    Rel(api, db, "Reads/Writes", "TCP")
    Rel(api, cache, "Caches", "TCP")
    Rel(api, worker, "Enqueues jobs", "Redis")
    Rel(worker, db, "Updates", "TCP")
    Rel(worker, storage, "Uploads", "HTTPS")
```
````

**Example**:

```mermaid
C4Container
    title Container Diagram for Blog Platform
    
    Person(reader, "Reader")
    Person(author, "Author")
    
    Container(web, "Web App", "Next.js", "Server-rendered blog")
    Container(api, "API", "Go", "RESTful API")
    Container(search, "Search Service", "Elasticsearch", "Full-text search")
    
    ContainerDb(db, "Database", "PostgreSQL", "Posts, users, comments")
    ContainerDb(cache, "Cache", "Redis", "Fragment caching")
    
    Rel(reader, web, "Reads posts", "HTTPS")
    Rel(author, web, "Writes posts", "HTTPS")
    Rel(web, api, "Fetches data", "JSON/HTTPS")
    Rel(web, search, "Searches", "JSON/HTTPS")
    Rel(api, db, "CRUD operations", "TCP")
    Rel(api, cache, "Caches queries", "TCP")
    Rel(search, db, "Indexes posts", "TCP")
```

### C4 Component

**Shows**: Major components within a container

**Template**:

````markdown
# Component Diagram

```mermaid
C4Component
    title Component Diagram for API Container
    
    Container_Boundary(api, "API") {
        Component(controller, "Controller", "Express Router", "HTTP handling")
        Component(service, "Service Layer", "Business logic")
        Component(repo, "Repository", "Data access")
        Component(auth, "Auth Middleware", "JWT validation")
    }
    
    ContainerDb(db, "Database", "PostgreSQL")
    
    Rel(controller, auth, "Validates", "function call")
    Rel(controller, service, "Calls", "function call")
    Rel(service, repo, "Uses", "function call")
    Rel(repo, db, "Queries", "SQL")
```
````

---

## Sequence Diagrams

**Shows**: Interactions between components over time

**Template**:

````markdown
# Sequence Diagram: {{INTERACTION_NAME}}

```mermaid
sequenceDiagram
    actor User
    participant Web
    participant API
    participant DB
    
    User->>Web: Click "Submit"
    activate Web
    Web->>API: POST /api/orders
    activate API
    API->>DB: INSERT order
    activate DB
    DB-->>API: Order ID
    deactivate DB
    API-->>Web: 201 Created
    deactivate API
    Web-->>User: Show success
    deactivate Web
```
````

**Example**: Authentication Flow

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant Backend
    participant AuthProvider
    participant Database
    
    User->>Frontend: Click "Login with Google"
    Frontend->>AuthProvider: Redirect to OAuth
    User->>AuthProvider: Enter credentials
    AuthProvider-->>Frontend: Redirect with code
    Frontend->>Backend: POST /auth/callback
    Backend->>AuthProvider: Exchange code for token
    AuthProvider-->>Backend: Access token + user info
    Backend->>Database: Create/update user
    Database-->>Backend: User ID
    Backend->>Backend: Generate JWT
    Backend-->>Frontend: JWT token
    Frontend-->>User: Redirect to dashboard
```

**PlantUML Alternative**:

```plantuml
@startuml
actor User
participant "Frontend" as FE
participant "Backend" as BE
database "Database" as DB

User -> FE: Submit form
activate FE
FE -> BE: POST /api/submit
activate BE
BE -> DB: INSERT data
activate DB
DB --> BE: Success
deactivate DB
BE --> FE: 200 OK
deactivate BE
FE --> User: Show confirmation
deactivate FE
@enduml
```

---

## Entity-Relationship Diagrams

**Shows**: Database schema and relationships

**Template**:

````markdown
# ER Diagram: Database Schema

```mermaid
erDiagram
    USER ||--o{ ORDER : places
    USER {
        uuid id PK
        string email
        string name
        timestamp created_at
    }
    ORDER ||--|{ ORDER_ITEM : contains
    ORDER {
        uuid id PK
        uuid user_id FK
        decimal total
        string status
        timestamp created_at
    }
    ORDER_ITEM {
        uuid id PK
        uuid order_id FK
        uuid product_id FK
        int quantity
        decimal price
    }
    PRODUCT ||--o{ ORDER_ITEM : "ordered in"
    PRODUCT {
        uuid id PK
        string name
        text description
        decimal price
        int stock
    }
```
````

**Example**: Blog Schema

```mermaid
erDiagram
    USER ||--o{ POST : writes
    USER ||--o{ COMMENT : writes
    USER {
        uuid id PK
        string username UK
        string email UK
        string password_hash
        timestamp created_at
    }
    POST ||--o{ COMMENT : has
    POST ||--o{ TAG : tagged_with
    POST {
        uuid id PK
        uuid author_id FK
        string title
        text content
        string slug UK
        timestamp published_at
        timestamp updated_at
    }
    COMMENT {
        uuid id PK
        uuid post_id FK
        uuid author_id FK
        text content
        timestamp created_at
    }
    TAG {
        uuid id PK
        string name UK
    }
```

---

## State Diagrams

**Shows**: State transitions and events

**Template**:

````markdown
# State Diagram: {{ENTITY}} Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> UnderReview: submit()
    UnderReview --> Approved: approve()
    UnderReview --> Rejected: reject()
    UnderReview --> Draft: request_changes()
    Approved --> Published: publish()
    Rejected --> Draft: revise()
    Published --> Archived: archive()
    Archived --> [*]
```
````

**Example**: Order State Machine

```mermaid
stateDiagram-v2
    [*] --> Draft: Create cart
    Draft --> Pending: Checkout
    Pending --> Paid: Payment successful
    Pending --> Cancelled: Payment failed/timeout
    Paid --> Shipped: Ship items
    Shipped --> Delivered: Delivery confirmed
    Paid --> Refunded: Refund requested
    Delivered --> Returned: Return initiated
    Returned --> Refunded: Refund processed
    Cancelled --> [*]
    Refunded --> [*]
    Delivered --> [*]: After 30 days
```

---

## Data Flow Diagrams

**Shows**: How data moves through the system

**Template**:

````markdown
# Data Flow: {{PROCESS_NAME}}

```mermaid
flowchart TD
    User[User Input] --> Validate{Valid?}
    Validate -->|No| Error[Show Error]
    Validate -->|Yes| Transform[Transform Data]
    Transform --> Save[(Save to DB)]
    Save --> Event[Emit Event]
    Event --> Notify[Send Notification]
    Event --> Index[Update Search Index]
    Notify --> Done[Complete]
    Index --> Done
```
````

**Example**: File Upload Flow

```mermaid
flowchart TD
    Upload[User uploads file] --> Check{File valid?}
    Check -->|No| Reject[Reject upload]
    Check -->|Yes| Scan[Virus scan]
    Scan --> Infected{Infected?}
    Infected -->|Yes| Quarantine[Quarantine file]
    Infected -->|No| Process[Process file]
    Process --> Thumbnail[Generate thumbnail]
    Process --> Extract[Extract metadata]
    Thumbnail --> Store[(Store in S3)]
    Extract --> Store
    Store --> DB[(Save to database)]
    DB --> Notify[Notify user]
    Notify --> Complete[Upload complete]
```

---

## Best Practices

### General Guidelines

✅ **Do**:
- Keep diagrams simple and focused
- Update diagrams when architecture changes
- Use consistent naming conventions
- Include legend if using custom symbols
- Date diagrams to show currency
- Link diagrams to relevant ADRs

❌ **Don't**:
- Create diagrams for every minor detail
- Let diagrams become outdated
- Use inconsistent notation
- Create overly complex diagrams
- Forget to commit diagram sources

### Choosing the Right Diagram

| To Show...                        | Use...                   |
| --------------------------------- | ------------------------ |
| System in its environment         | C4 Context               |
| Major technology choices          | C4 Container             |
| Internal structure                | C4 Component             |
| Request/response flow             | Sequence Diagram         |
| Database schema                   | ER Diagram               |
| State transitions                 | State Diagram            |
| Data processing pipeline          | Data Flow Diagram        |
| Deployment architecture           | Deployment Diagram       |
| Network topology                  | Network Diagram          |

### Naming Conventions

**Files**: `{type}-{name}.md` or `{name}-{type}.md`

Examples:
- `system-context.md`
- `user-authentication-sequence.md`
- `database-er-diagram.md`
- `order-state-machine.md`

### Keeping Diagrams Current

**Triggers for update**:
- Architectural decision (ADR) made
- New service/component added
- Integration point changed
- State machine logic updated
- Database schema modified

**Review schedule**:
- **Quarterly**: Full diagram audit
- **Per release**: Update affected diagrams
- **Per ADR**: Create/update relevant diagram

---

## Tools Comparison

### Mermaid

**Pros**:
- ✅ Native GitHub rendering
- ✅ Text-based (version control friendly)
- ✅ Wide tooling support
- ✅ Simple syntax
- ✅ No external dependencies for viewing

**Cons**:
- ❌ Less expressive than PlantUML
- ❌ Limited customization
- ❌ Fewer diagram types

**Best for**: Most use cases, team collaboration

### PlantUML

**Pros**:
- ✅ Very expressive
- ✅ Many diagram types
- ✅ Mature and stable
- ✅ Extensive customization

**Cons**:
- ❌ Requires Java runtime or external service
- ❌ GitHub doesn't render directly
- ❌ Steeper learning curve

**Best for**: Complex diagrams, detailed documentation

### Draw.io / Lucidchart

**Pros**:
- ✅ WYSIWYG editor
- ✅ Easy for non-technical users
- ✅ Beautiful diagrams

**Cons**:
- ❌ Binary files (poor for version control)
- ❌ Requires external tool
- ❌ Harder to keep in sync with code

**Best for**: Presentations, stakeholder communication

**Recommendation**: Use Mermaid as default, PlantUML for complex cases, Draw.io for presentations.

---

## Examples in This Directory

[Add links to your actual diagram files here]

- [System Context](./system-context.md)
- [Container Diagram](./container.md)
- [Authentication Sequence](./auth-sequence.md)
- [Database Schema](./database-er.md)
- [Order State Machine](./order-states.md)

---

## Learning Resources

### Mermaid

- **Official Docs**: https://mermaid.js.org/
- **Live Editor**: https://mermaid.live/
- **GitHub Guide**: https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams

### PlantUML

- **Official Site**: https://plantuml.com/
- **Guide**: https://plantuml.com/guide
- **Examples**: https://real-world-plantuml.com/

### C4 Model

- **Official Site**: https://c4model.com/
- **Diagrams**: https://c4model.com/#Diagrams
- **Mermaid C4**: https://mermaid.js.org/syntax/c4c.html

### General Architecture Diagramming

- **C4 Model Guide**: https://c4model.com/
- **Simon Brown's Site**: https://simonbrown.je/
- **Software Architecture Guide**: https://martinfowler.com/architecture/

---

## Contributing

When adding new diagrams:

1. Follow naming conventions
2. Use templates from this README
3. Add entry to "Examples" section above
4. Link from relevant documentation
5. Reference in ADR if architectural decision
6. Test rendering (GitHub, VS Code, or online tool)

---

**Document Version**: 1.0
**Last Updated**: 2025-12-17
**Maintained By**: Development Team
**Feedback**: Open GitHub issue with "diagrams:" prefix

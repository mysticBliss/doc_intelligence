## Core Evaluation Framework
For every feature/component, analyze through:

**Enterprise Pillars**
- Security & Compliance (data classification, encryption, audit trails, regulatory requirements)
- Data Governance (metadata, lineage, quality, retention, master data management)
- Integration Architecture (APIs, event-driven patterns, enterprise service bus, legacy compatibility)
- Scalability & Performance (horizontal scaling, load balancing, capacity planning, multi-tenancy)
- Operational Excellence (monitoring, DevOps integration, maintainability, documentation)

**Python Enterprise Patterns (Mandatory)**
- **Hexagonal Architecture**: Ports & adapters for external dependencies isolation
- **Domain-Driven Design**: Bounded contexts, aggregate roots, repository pattern
- **CQRS**: Separate read/write models with command/query handlers
- **Factory & Strategy**: Plugin architecture with Protocol classes for extensibility
- **Dependency Injection**: Configuration-driven component wiring
- **Decorator Pattern**: Cross-cutting concerns (audit, security, monitoring)
- **Circuit Breaker & Saga**: Resilience and distributed transaction handling

**Code Quality Standards**
- Type hints with mypy strict mode, Pydantic validation
- Structured logging with correlation IDs for distributed tracing
- FastAPI/SQLAlchemy for type-safe APIs and data access
- Comprehensive testing (unit, integration, contract, property-based)
- Black/Ruff formatting, Bandit security scanning

## Response Structure
Always provide:
1. **Enterprise Risk Assessment** - Scale and integration risks
2. **Pattern Compliance** - Required Python patterns and architecture decisions
3. **Quality Gates** - Type safety, testing, security requirements  
4. **Integration Strategy** - Enterprise ecosystem fit and API design
5. **Implementation Roadmap** - Phased approach with architectural milestones

## Key Challenge Questions
- How does this scale to enterprise volumes with proper resource management?
- Which Python patterns ensure modularity and testability?
- What are the data governance and compliance implications?
- How does this integrate with existing enterprise Python toolchain?
- What happens during failure scenarios and how do we recover?
- Can this be deployed, monitored, and maintained by enterprise ops teams?

## Decision Criteria
Prioritize: Enterprise integration > Long-term maintainability > Developer productivity > Feature completeness

## Project Working
REMEMBER I AM USING DOCKER COMPOSE THAT HOSTED MY PLATFORM. suggest changes based on that since i cant run commands
All commands, especially for testing and validation, must be executed within the context of the appropriate service container.

## logging. 
dont introduce any new logging libraries. use the existing structlog logger

## PDF and Images linkage
For any PDF we should has a unique ID and then, under it we have Images which are also unique by ID however, there should be a relation between the PDF and the images ; a father son relationship. Howver, when we only upload an Image or we have only single image in PDF then we dont need store parent son relationship.

## API Endpoints
- All API endpoints must be fully functional and thoroughly tested.
- The API implementation should be **enterprise-grade**, addressing the following key areas:
  - Security (authentication, authorization, encryption)
  - Scalability and performance
  - Reliability and fault tolerance
  - Compliance with relevant standards and regulations
  - Clear documentation for each endpoint
- Future UI applications will be built to rely exclusively on this API for all functionality.
- The API must support robust integration and extensibility for future requirements.
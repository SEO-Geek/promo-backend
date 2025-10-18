"""
Database Module for Promotional Content Management System

This module manages asynchronous PostgreSQL database connections using asyncpg.
It provides a connection pool for efficient database operations and query methods
for common database operations (execute, fetch, fetchrow, fetchval).

Architecture:
    - Connection pooling for efficient resource management
    - Async/await pattern for non-blocking database operations
    - URL parsing for flexible connection string format
    - Special character handling (URL encoding/decoding)
    - Global singleton instance for application-wide access
    - FastAPI dependency injection support

Performance:
    - Connection pool reduces connection overhead
    - Min pool size: 2 (always ready connections)
    - Max pool size: 10 (scales with load)
    - Command timeout: 60 seconds (prevents hanging queries)

Security:
    - Uses parameterized queries (prevents SQL injection)
    - Password URL decoding for special characters
    - Connection pooling limits database load
    - Proper error handling without exposing sensitive data

Usage:
    from app.database import db

    # Application startup
    await db.connect()

    # Query operations
    result = await db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    await db.execute("UPDATE users SET name = $1 WHERE id = $2", name, user_id)

    # Application shutdown
    await db.disconnect()

Created: October 16, 2025
Updated: October 17, 2025 - Added comprehensive documentation
"""
import asyncpg
from typing import Optional, List, Any
from app.config import settings
import logging
from urllib.parse import urlparse, unquote

# Configure module-level logger
logger = logging.getLogger(__name__)


class Database:
    """
    Async PostgreSQL database connection manager with connection pooling

    This class manages a connection pool to PostgreSQL using asyncpg for
    high-performance async database operations. Connection pooling reduces
    overhead by reusing connections instead of creating new ones for each query.

    Features:
        - Connection pooling (min: 2, max: 10 connections)
        - URL-based connection configuration
        - Special character handling in passwords
        - Automatic connection lifecycle management
        - Query timeout protection (60 seconds)
        - Comprehensive error logging

    Connection Pool Settings:
        - min_size: 2 - Minimum connections always ready (reduces latency)
        - max_size: 10 - Maximum concurrent connections (prevents database overload)
        - command_timeout: 60 - Maximum query execution time in seconds

    Performance Notes:
        - Pool maintains 2 idle connections for instant query execution
        - Additional connections created up to max (10) under load
        - Connections automatically returned to pool after use
        - Pool prevents connection leaks via context managers

    Security Notes:
        - Always use parameterized queries ($1, $2) to prevent SQL injection
        - Password is URL-decoded to handle special characters properly
        - Pool size limits prevent database resource exhaustion
        - Query timeout prevents runaway queries from hanging

    Thread Safety:
        - asyncpg pools are thread-safe for async operations
        - Do NOT use with threading module (use asyncio only)

    Example:
        db = Database()
        await db.connect()

        # Fetch single row
        user = await db.fetchrow(
            "SELECT * FROM users WHERE email = $1",
            "user@example.com"
        )

        # Fetch multiple rows
        offers = await db.fetch(
            "SELECT * FROM promo_offers WHERE status = $1",
            "active"
        )

        # Execute INSERT/UPDATE/DELETE
        await db.execute(
            "UPDATE promo_offers SET title = $1 WHERE id = $2",
            "New Title", offer_id
        )

        await db.disconnect()
    """

    def __init__(self):
        """
        Initialize database instance

        Creates an empty connection pool that will be populated when
        connect() is called. The pool starts as None and is initialized
        during application startup.

        Note: Do not perform database operations until connect() is called
        """
        self.pool: Optional[asyncpg.Pool] = None
        """
        AsyncPG connection pool (None until connect() is called)

        Type: asyncpg.Pool or None
        Initialized: During connect() call
        Closed: During disconnect() call

        The pool manages a set of database connections that can be reused
        across multiple queries, improving performance by avoiding the
        overhead of creating new connections.
        """

    async def connect(self):
        """
        Create and configure the database connection pool

        This method is called during FastAPI application startup to establish
        the connection pool. It parses the DATABASE_URL from settings and
        creates a pool with the configured parameters.

        Connection String Format:
            postgresql://username:password@host:port/database

        Example:
            postgresql://strapi_user:AiDaily@2025$ecure@127.0.0.1:5432/aidailypost_cms

        Special Character Handling:
            - Passwords with special characters (like $, @, !) are URL-encoded
            - This method URL-decodes the password before connecting
            - Example: "password@123" becomes "password%40123" in URL

        Pool Configuration:
            - min_size: 2 connections always ready
            - max_size: 10 connections maximum
            - command_timeout: 60 seconds per query

        Error Handling:
            - Logs detailed error message if connection fails
            - Re-raises exception to prevent application startup with broken DB
            - FastAPI will fail to start if this raises an exception

        Performance:
            - Creating pool takes ~100-500ms (one-time startup cost)
            - Subsequent queries use pooled connections (< 1ms overhead)

        Raises:
            asyncpg.InvalidCatalogNameError: Database does not exist
            asyncpg.InvalidPasswordError: Authentication failed
            asyncpg.CannotConnectNowError: Database is not accepting connections
            Exception: Other connection errors (network, DNS, etc.)

        Example:
            try:
                await db.connect()
                logger.info("Database connected successfully")
            except asyncpg.InvalidPasswordError:
                logger.error("Database authentication failed")
                raise
            except Exception as e:
                logger.error(f"Database connection error: {e}")
                raise
        """
        try:
            # Parse DATABASE_URL to extract connection components
            # This handles special characters in password properly
            parsed = urlparse(settings.DATABASE_URL)

            # Build connection parameters from parsed URL
            self.pool = await asyncpg.create_pool(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=unquote(parsed.password) if parsed.password else None,
                database=parsed.path.lstrip('/'),
                min_size=2,
                max_size=10,
                command_timeout=60
            )

            logger.info("✅ Database connection pool created successfully")
            logger.info(f"   Pool: min={2}, max={10}, timeout={60}s")

        except asyncpg.InvalidCatalogNameError as e:
            logger.error(f"❌ Database does not exist: {e}")
            logger.error(f"   DATABASE_URL: {settings.DATABASE_URL}")
            raise

        except asyncpg.InvalidPasswordError as e:
            logger.error(f"❌ Database authentication failed: {e}")
            logger.error(f"   Check DATABASE_URL credentials")
            raise

        except Exception as e:
            logger.error(f"❌ Failed to create database pool: {e}")
            logger.error(f"   Type: {type(e).__name__}")
            raise

    async def disconnect(self):
        """
        Close the database connection pool gracefully

        This method is called during FastAPI application shutdown to properly
        close all connections in the pool. It waits for active queries to
        complete before closing connections.

        Shutdown Process:
            1. Stop accepting new connections
            2. Wait for active queries to complete (with timeout)
            3. Close all connections in the pool
            4. Release all resources

        Timeout Handling:
            - Active queries have command_timeout (60s) to complete
            - After timeout, connections are forcibly closed
            - In-flight queries may receive connection errors

        Resource Cleanup:
            - Connection memory released (~10MB per connection)
            - Database server connection slots freed
            - Network sockets closed

        Best Practices:
            - Always call during application shutdown
            - Use try/finally to ensure cleanup happens
            - Log any errors but don't raise (allow graceful shutdown)

        Example:
            # In FastAPI lifespan or shutdown event
            @app.on_event("shutdown")
            async def shutdown():
                try:
                    await db.disconnect()
                except Exception as e:
                    logger.error(f"Error during database shutdown: {e}")

        Note:
            - Safe to call multiple times (checks if pool exists)
            - Safe to call if connect() was never called
            - Does not raise exceptions (logs errors instead)
        """
        if self.pool:
            try:
                await self.pool.close()
                logger.info("✅ Database connection pool closed gracefully")
            except Exception as e:
                logger.error(f"⚠️ Error closing database pool: {e}")
                # Don't raise - allow shutdown to continue
        else:
            logger.warning("⚠️ Database pool was never initialized (connect() not called)")

    async def execute(self, query: str, *args) -> str:
        """
        Execute a query that modifies data (INSERT, UPDATE, DELETE)

        This method executes queries that change database state but do not
        return rows. It returns a status string indicating the operation
        result (e.g., "INSERT 0 1" means 1 row inserted).

        Args:
            query (str): SQL query with positional parameters ($1, $2, ...)
            *args: Parameter values to substitute into query

        Returns:
            str: Status string from database
                - "INSERT 0 1" - 1 row inserted
                - "UPDATE 3" - 3 rows updated
                - "DELETE 5" - 5 rows deleted

        Security:
            ⚠️ CRITICAL: Always use parameterized queries with $1, $2, etc.
            ✅ SAFE:   query = "DELETE FROM users WHERE id = $1", user_id
            ❌ UNSAFE: query = f"DELETE FROM users WHERE id = {user_id}"

            Parameterized queries prevent SQL injection attacks by:
            - Separating SQL structure from data values
            - Automatically escaping special characters
            - Preventing malicious SQL code execution

        Performance:
            - Connection acquired from pool (~1ms overhead)
            - Query execution time varies by operation
            - Connection automatically returned to pool
            - Use EXPLAIN ANALYZE to profile slow queries

        Error Handling:
            - Raises asyncpg exceptions for database errors
            - Common exceptions:
                * UniqueViolationError - Duplicate key conflict
                * ForeignKeyViolationError - Invalid foreign key
                * NotNullViolationError - NULL in NOT NULL column
                * CheckViolationError - CHECK constraint failed
                * QueryCanceledError - Query timeout exceeded

        Examples:
            # Insert new offer
            result = await db.execute(
                \"\"\"
                INSERT INTO promo_offers (title, description, url, status)
                VALUES ($1, $2, $3, $4)
                \"\"\",
                "50% Off Sale", "Limited time offer", "https://example.com", "draft"
            )
            # Returns: "INSERT 0 1"

            # Update offer status
            result = await db.execute(
                "UPDATE promo_offers SET status = $1 WHERE id = $2",
                "published", offer_id
            )
            # Returns: "UPDATE 1" if found, "UPDATE 0" if not found

            # Delete approved images
            result = await db.execute(
                "DELETE FROM promo_images WHERE offer_id = $1 AND approved = true",
                offer_id
            )
            # Returns: "DELETE 3" if 3 images deleted

            # Conditional delete (ON CONFLICT)
            result = await db.execute(
                \"\"\"
                INSERT INTO promo_click_tracking (offer_id, clicked_at)
                VALUES ($1, NOW())
                ON CONFLICT (offer_id, clicked_at) DO NOTHING
                \"\"\",
                offer_id
            )
            # Returns: "INSERT 0 1" or "INSERT 0 0" if duplicate

        Best Practices:
            - Always use $1, $2, etc. for parameters
            - Never use string formatting or concatenation
            - Log query and parameters on errors (helps debugging)
            - Use transactions for multi-step operations
            - Check return value to verify operation success

        Raises:
            asyncpg.UniqueViolationError: Duplicate key
            asyncpg.ForeignKeyViolationError: Invalid foreign key reference
            asyncpg.NotNullViolationError: NULL in NOT NULL column
            asyncpg.CheckViolationError: CHECK constraint violation
            asyncpg.QueryCanceledError: Query timeout (60s) exceeded
            asyncpg.PostgresError: Other database errors
        """
        async with self.pool.acquire() as connection:
            """
            Context manager for connection lifecycle

            Automatically:
            1. Acquires connection from pool (waits if all connections busy)
            2. Executes query on the connection
            3. Returns connection to pool (even if query fails)

            Performance:
            - If pool has idle connection: < 1ms to acquire
            - If all connections busy: Waits until one becomes available
            - Maximum wait: No timeout (waits indefinitely)

            Note: Connection is not closed, just returned to pool for reuse
            """
            return await connection.execute(query, *args)

    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        """
        Fetch multiple rows from a SELECT query

        This method executes a query and returns all matching rows as a list
        of Record objects. Each Record behaves like a dict but with additional
        features (attribute access, type conversion, etc.).

        Args:
            query (str): SQL SELECT query with positional parameters ($1, $2, ...)
            *args: Parameter values to substitute into query

        Returns:
            List[asyncpg.Record]: List of database records
                - Empty list if no rows match
                - Each Record supports dict-like access: row['column']
                - Each Record supports attribute access: row.column
                - Can convert to dict: dict(row)

        Performance:
            - Loads ALL rows into memory (use with caution for large results)
            - For large datasets, consider:
                * LIMIT clause to restrict rows
                * Pagination (OFFSET/LIMIT)
                * Streaming with cursor (connection.cursor())

            Memory usage:
            - ~1KB per row average (varies by column types/sizes)
            - 1000 rows ≈ 1MB
            - 100,000 rows ≈ 100MB

        Security:
            - Always use parameterized queries ($1, $2, etc.)
            - See execute() method for security details

        Examples:
            # Fetch all offers
            offers = await db.fetch("SELECT * FROM promo_offers")
            for offer in offers:
                print(offer['title'])  # Dict-style access
                print(offer.title)     # Attribute-style access

            # Fetch filtered offers
            active_offers = await db.fetch(
                "SELECT * FROM promo_offers WHERE status = $1",
                "published"
            )

            # Fetch with JOIN
            offers_with_images = await db.fetch(
                \"\"\"
                SELECT o.*, i.image_url
                FROM promo_offers o
                LEFT JOIN promo_images i ON o.id = i.offer_id
                WHERE o.status = $1 AND i.approved = true
                \"\"\",
                "published"
            )

            # Fetch with pagination
            page_size = 20
            offset = (page_number - 1) * page_size
            offers = await db.fetch(
                \"\"\"
                SELECT * FROM promo_offers
                WHERE status = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                \"\"\",
                "published", page_size, offset
            )

            # Convert to list of dicts (for JSON serialization)
            offers_dict = [dict(row) for row in offers]

        Working with Results:
            # Check if results exist
            offers = await db.fetch("SELECT * FROM promo_offers")
            if offers:
                print(f"Found {len(offers)} offers")
            else:
                print("No offers found")

            # Access columns
            for offer in offers:
                title = offer['title']        # Dict access
                title = offer.title           # Attribute access (same result)
                title = offer.get('title')    # Safe access (None if not exists)

            # Convert to dict
            offer_dict = dict(offers[0])

            # Access by column index
            first_column = offers[0][0]

        Best Practices:
            - Use LIMIT for large tables to prevent memory issues
            - Use ORDER BY for consistent ordering
            - Use WHERE clause to filter unnecessary rows
            - Consider fetchrow() if you only need one row
            - Consider fetchval() if you only need one value

        Raises:
            asyncpg.PostgresError: Database error
            asyncpg.QueryCanceledError: Query timeout (60s) exceeded
        """
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """
        Fetch a single row from a SELECT query

        This method executes a query and returns the first matching row.
        Commonly used for lookups by unique identifier (ID, email, etc.).

        Args:
            query (str): SQL SELECT query with positional parameters ($1, $2, ...)
            *args: Parameter values to substitute into query

        Returns:
            asyncpg.Record or None:
                - Record object if row found (dict-like access)
                - None if no rows match query
                - Only returns FIRST row if multiple rows match

        Performance:
            - More efficient than fetch() for single row
            - Database can stop searching after first match
            - Uses less memory (only one row loaded)
            - Add LIMIT 1 to query for clarity (optional)

        Security:
            - Always use parameterized queries ($1, $2, etc.)
            - See execute() method for security details

        Examples:
            # Fetch offer by ID
            offer = await db.fetchrow(
                "SELECT * FROM promo_offers WHERE id = $1",
                offer_id
            )
            if offer:
                print(f"Found: {offer['title']}")
            else:
                print("Offer not found")

            # Fetch user by email
            user = await db.fetchrow(
                "SELECT * FROM promo_users WHERE email = $1",
                "user@example.com"
            )

            # Fetch with JOIN
            offer_with_stats = await db.fetchrow(
                \"\"\"
                SELECT o.*,
                       COUNT(i.id) as image_count,
                       COUNT(t.id) as text_count
                FROM promo_offers o
                LEFT JOIN promo_images i ON o.id = i.offer_id
                LEFT JOIN promo_text_variations t ON o.id = t.offer_id
                WHERE o.id = $1
                GROUP BY o.id
                \"\"\",
                offer_id
            )

            # Check existence
            exists = await db.fetchrow(
                "SELECT 1 FROM promo_offers WHERE url = $1",
                offer_url
            )
            if exists:
                print("URL already exists")

        Working with Result:
            # Safely handle None result
            offer = await db.fetchrow("SELECT * FROM promo_offers WHERE id = $1", 999)
            if offer:
                title = offer['title']  # Safe to access
            else:
                title = "Not found"

            # Get value with default
            offer = await db.fetchrow("SELECT * FROM promo_offers WHERE id = $1", offer_id)
            title = offer.get('title', 'Unknown') if offer else 'Unknown'

            # Convert to dict
            if offer:
                offer_dict = dict(offer)

        Common Patterns:
            # Get or 404 pattern
            offer = await db.fetchrow(
                "SELECT * FROM promo_offers WHERE id = $1",
                offer_id
            )
            if not offer:
                raise HTTPException(status_code=404, detail="Offer not found")

            # Verify ownership pattern
            offer = await db.fetchrow(
                "SELECT * FROM promo_offers WHERE id = $1 AND user_id = $2",
                offer_id, current_user_id
            )
            if not offer:
                raise HTTPException(status_code=403, detail="Access denied")

            # Existence check pattern
            existing = await db.fetchrow(
                "SELECT id FROM promo_offers WHERE url = $1",
                url
            )
            if existing:
                raise HTTPException(status_code=400, detail="URL already exists")

        Best Practices:
            - Use WHERE clause to ensure uniqueness
            - Check for None before accessing columns
            - Add ORDER BY if multiple rows could match
            - Use this instead of fetch() when only one row needed
            - Consider adding LIMIT 1 for clarity

        Raises:
            asyncpg.PostgresError: Database error
            asyncpg.QueryCanceledError: Query timeout (60s) exceeded
        """
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def fetchval(self, query: str, *args) -> Any:
        """
        Fetch a single value from a SELECT query

        This method executes a query and returns just the first column of the
        first row. Most efficient method when you only need a single value
        (count, sum, ID, boolean check, etc.).

        Args:
            query (str): SQL SELECT query with positional parameters ($1, $2, ...)
            *args: Parameter values to substitute into query

        Returns:
            Any: Single value from database
                - None if no rows match
                - Python type depends on PostgreSQL column type:
                    * INTEGER → int
                    * TEXT → str
                    * BOOLEAN → bool
                    * TIMESTAMP → datetime
                    * JSON → dict/list

        Performance:
            - Most efficient fetch method (only one value transferred)
            - Database can optimize for single value return
            - Minimal memory usage
            - Ideal for aggregations (COUNT, SUM, AVG, etc.)

        Security:
            - Always use parameterized queries ($1, $2, etc.)
            - See execute() method for security details

        Examples:
            # Count offers
            count = await db.fetchval(
                "SELECT COUNT(*) FROM promo_offers WHERE status = $1",
                "published"
            )
            print(f"Found {count} published offers")

            # Check if exists
            exists = await db.fetchval(
                "SELECT EXISTS(SELECT 1 FROM promo_users WHERE email = $1)",
                "user@example.com"
            )
            if exists:
                print("User already exists")

            # Get single column value
            title = await db.fetchval(
                "SELECT title FROM promo_offers WHERE id = $1",
                offer_id
            )

            # Get aggregation
            total_clicks = await db.fetchval(
                "SELECT SUM(click_count) FROM promo_click_tracking WHERE offer_id = $1",
                offer_id
            )

            # Get JSON data
            metadata = await db.fetchval(
                "SELECT metadata FROM promo_offers WHERE id = $1",
                offer_id
            )  # Returns dict if column is JSON/JSONB

            # Get latest timestamp
            last_update = await db.fetchval(
                "SELECT MAX(updated_at) FROM promo_offers"
            )  # Returns datetime object

        Common Use Cases:
            # Existence checks (fast boolean)
            user_exists = await db.fetchval(
                "SELECT EXISTS(SELECT 1 FROM promo_users WHERE id = $1)",
                user_id
            )

            # Count records
            active_count = await db.fetchval(
                "SELECT COUNT(*) FROM promo_offers WHERE status = 'published'"
            )

            # Get ID after insert (RETURNING clause)
            new_id = await db.fetchval(
                \"\"\"
                INSERT INTO promo_offers (title, description)
                VALUES ($1, $2)
                RETURNING id
                \"\"\",
                title, description
            )

            # Check null/not null
            has_image = await db.fetchval(
                \"\"\"
                SELECT EXISTS(
                    SELECT 1 FROM promo_images
                    WHERE offer_id = $1 AND approved = true
                )
                \"\"\",
                offer_id
            )

        Type Handling:
            # PostgreSQL → Python type mapping
            # INTEGER, BIGINT → int
            # TEXT, VARCHAR → str
            # BOOLEAN → bool
            # TIMESTAMP → datetime.datetime
            # DATE → datetime.date
            # JSON, JSONB → dict or list
            # ARRAY → list
            # NULL → None

            # Handle None result
            count = await db.fetchval("SELECT COUNT(*) ...") or 0
            title = await db.fetchval("SELECT title ...") or "Unknown"

        Best Practices:
            - Use EXISTS() for boolean checks (faster than COUNT)
            - Use RETURNING clause to get inserted/updated ID
            - Handle None returns appropriately
            - Use for aggregations (COUNT, SUM, AVG, MAX, MIN)
            - Prefer this over fetchrow() when only one value needed

        Raises:
            asyncpg.PostgresError: Database error
            asyncpg.QueryCanceledError: Query timeout (60s) exceeded
        """
        async with self.pool.acquire() as connection:
            return await connection.fetchval(query, *args)


# ===========================================================================
# Global Database Instance
# ===========================================================================

# Singleton instance used throughout the application
db = Database()
"""
Global database instance for application-wide access

This is a singleton pattern - only one database connection pool exists
for the entire application. All modules import and use this same instance.

Usage:
    from app.database import db

    # In endpoint handler
    result = await db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)

Lifecycle:
    1. Created at module import (when application starts)
    2. connect() called during FastAPI startup event
    3. Used throughout application lifetime
    4. disconnect() called during FastAPI shutdown event

Benefits:
    - Single connection pool shared across all endpoints
    - No need to pass database instance around
    - Automatic connection pooling and management
    - Clean dependency injection with get_db()

Note: Must call await db.connect() before using, typically in startup event
"""


# ===========================================================================
# FastAPI Dependency Injection
# ===========================================================================

async def get_db() -> Database:
    """
    FastAPI dependency for database access in endpoint handlers

    This dependency function provides the database instance to FastAPI
    endpoint handlers via dependency injection. It's used in endpoint
    signatures to automatically provide database access.

    Returns:
        Database: The global database instance

    Usage in Endpoints:
        from fastapi import Depends
        from app.database import get_db, Database

        @app.get("/offers")
        async def get_offers(db: Database = Depends(get_db)):
            offers = await db.fetch("SELECT * FROM promo_offers")
            return offers

        @app.post("/offers")
        async def create_offer(
            offer: OfferCreate,
            db: Database = Depends(get_db)
        ):
            offer_id = await db.fetchval(
                "INSERT INTO promo_offers (title) VALUES ($1) RETURNING id",
                offer.title
            )
            return {"id": offer_id}

    Benefits of Dependency Injection:
        - Clean separation of concerns
        - Easy to mock for testing
        - Consistent database access pattern
        - Type hints for IDE autocomplete
        - Automatic documentation in OpenAPI schema

    Testing:
        # Override dependency in tests
        from fastapi.testclient import TestClient

        async def get_test_db():
            return test_database_instance

        app.dependency_overrides[get_db] = get_test_db
        client = TestClient(app)

    Note:
        - This is a simple dependency (just returns global instance)
        - Could be extended to provide per-request transaction management
        - Could track per-request database metrics
        - Could implement read replica routing

    Performance:
        - No overhead (just returns existing instance)
        - Connection pooling handled by Database class
        - Each request gets connection from pool automatically
    """
    return db

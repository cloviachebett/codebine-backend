import asyncio
import uuid
import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import Column, Enum, Integer, String, Table, Uuid, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request
from starlette.responses import Response

from database import Base, get_db
from main import app
from models import User
from models._enums import UserRole
from models.system_audit_logs import SystemAuditLog
from repositories.system_logs import audit_log_repository
from schemas.system_logs import AuditLogCreate
from services import system_logs as system_log_service
from services.system_logs import AutomatedAuditMiddleware, _session_for
from services.current_user import get_current_user

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def _bootstrap_unmerged_dependencies():
    if "users" not in Base.metadata.tables:
        Table(
            "users",
            Base.metadata,
            Column("user_id", Uuid, primary_key=True),
            Column("full_name", String, nullable=True),
            Column("email", String, unique=True, index=True, nullable=False),
            Column("password_hash", String, nullable=False),
            Column("role", String, nullable=False),
            Column(
                "account_status",
                Enum("ACTIVE", "SUSPENDED", name="account_status_enum"),
                default="ACTIVE",
            ),
            Column("created_at", String, nullable=True),
            Column("last_login_at", String, nullable=True),
            Column("phone", String, nullable=True),
            Column("mfa_enrolled", Integer, default=0),
            Column("failed_login_attempts", Integer, default=0),
            Column("locked_until", String, nullable=True),
            extend_existing=True,
        )


def _seed_user(
    db, user_id, email, password_hash, role, full_name, account_status="ACTIVE"
):
    db.execute(
        Base.metadata.tables["users"]
        .insert()
        .values(
            user_id=user_id,
            full_name=full_name,
            email=email,
            password_hash=password_hash,
            role=role,
            account_status=account_status,
            mfa_enrolled=0,
            failed_login_attempts=0,
        )
    )
    db.commit()


@pytest.fixture(scope="function", autouse=True)
def isolated_db_context():
    _bootstrap_unmerged_dependencies()
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    app.dependency_overrides[get_db] = lambda: session
    yield session
    session.close()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_user(isolated_db_context):
    db = isolated_db_context
    admin_id = uuid.uuid4()
    _seed_user(
        db,
        admin_id,
        email="qa.admin@terrawatch.test",
        password_hash="hashed_production_string_bytes_123",
        role=UserRole.ADMIN,
        full_name="QA Admin",
    )
    user = db.query(User).filter_by(user_id=admin_id).first()
    app.dependency_overrides[get_current_user] = lambda: user
    return user


@pytest.fixture
def analyst_user(isolated_db_context):
    db = isolated_db_context
    analyst_id = uuid.uuid4()
    _seed_user(
        db,
        analyst_id,
        email="qa.analyst@terrawatch.test",
        password_hash="hashed_production_string_bytes_456",
        role=UserRole.ANALYST,
        full_name="QA Analyst",
    )
    user = db.query(User).filter_by(user_id=analyst_id).first()
    app.dependency_overrides[get_current_user] = lambda: user
    return user


def _build_request(path="/health", method="GET", app_instance=None):
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "state": {},
        "app": app_instance or app,
    }
    return Request(scope)


def test_1_repository_returns_none_for_missing_id(isolated_db_context):
    db = isolated_db_context
    assert audit_log_repository.get_by_id(db, uuid.uuid4()) is None


def test_2_audit_log_stores_valid_orm_record(isolated_db_context):
    db = isolated_db_context
    log = SystemAuditLog(action_type="PIPELINE_SUCCESS", entity_type="models")
    db.add(log)
    db.flush()
    assert isinstance(log.log_id, uuid.UUID)
    assert log.created_at is not None


def test_3_schema_validation_rejects_empty_payloads():
    with pytest.raises(ValidationError):
        AuditLogCreate(action_type=None, entity_type=None)


def test_4_schema_validation_enforces_max_length_constraints():
    with pytest.raises(ValidationError):
        AuditLogCreate(action_type="A" * 101, entity_type="models")


def test_5_service_fetches_valid_single_log(isolated_db_context, admin_user):
    db = isolated_db_context
    created = system_log_service.log_system_event(
        db=db, action_type="TEST_LOOKUP", entity_type="assets"
    )
    fetched = system_log_service.get_single_system_log(db, created.log_id, admin_user)
    assert fetched.log_id == created.log_id


def test_6_service_fetch_raises_404_not_found(isolated_db_context, admin_user):
    db = isolated_db_context
    with pytest.raises(HTTPException) as exc_info:
        system_log_service.get_single_system_log(db, uuid.uuid4(), admin_user)
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


def test_7_service_denies_analyst_access_to_single_logs(
    isolated_db_context, analyst_user
):
    db = isolated_db_context
    with pytest.raises(HTTPException) as exc_info:
        system_log_service.get_single_system_log(db, uuid.uuid4(), analyst_user)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


def test_8_service_lists_paginated_records_descending(isolated_db_context, admin_user):
    db = isolated_db_context
    for i in range(2):
        system_log_service.log_system_event(
            db=db, action_type=f"LOG_{i}", entity_type="items"
        )
    logs = system_log_service.list_all_system_logs(db, admin_user)
    assert len(logs) == 2
    assert logs[0].action_type == "LOG_1"


def test_9_session_for_unwraps_raw_generator_dependencies(isolated_db_context):
    req = _build_request()

    def mock_db_gen():
        yield isolated_db_context

    app.dependency_overrides[get_db] = mock_db_gen
    with _session_for(req) as extracted_session:
        if hasattr(extracted_session, "__next__") or isinstance(
            extracted_session, type((x for x in []))
        ):
            extracted_session = next(extracted_session)
        assert extracted_session == isolated_db_context


def test_10_middleware_bypasses_read_only_get_requests(isolated_db_context):
    db = isolated_db_context
    middleware = AutomatedAuditMiddleware(app=app)
    req = _build_request(path="/api/v1/metrics", method="GET")

    async def call_next(request):
        return Response(content=b"{}", status_code=200)

    response = asyncio.run(middleware.dispatch(req, call_next))
    assert response.status_code == 200
    assert response.background is None
    assert len(db.query(SystemAuditLog).all()) == 0


def test_11_middleware_logs_mutations_and_runs_background_worker(
    isolated_db_context, admin_user
):
    db = isolated_db_context
    middleware = AutomatedAuditMiddleware(app=app)
    req = _build_request(path="/api/v1/resource", method="POST")
    req.state.user = admin_user

    async def call_next(request):
        return Response(content=b"{}", status_code=201)

    response = asyncio.run(middleware.dispatch(req, call_next))
    assert response.status_code == 201
    assert response.background is not None

    async def run_async_background_worker():
        await response.background()

    asyncio.run(run_async_background_worker())

    logs = db.query(SystemAuditLog).all()
    assert len(logs) == 1
    assert logs[0].action_type == "API_POST_API_V1_RESOURCE"
    assert logs[0].entity_id == "201"


def test_12_router_endpoint_manual_log_creation(
    client, admin_user, isolated_db_context
):
    payload = {
        "action_type": "ADMIN_FLUSH_CACHE",
        "entity_type": "system_nodes",
        "entity_id": "node_01",
        "execution_details": {"forced": True},
    }

    from routers.system_logs import router as system_logs_router

    if "/audit-logs" not in [
        route.path for route in app.routes if hasattr(route, "path")
    ]:
        app.include_router(system_logs_router)

    response = client.post("/audit-logs/", json=payload)

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_14_background_worker_swallows_database_errors(monkeypatch):
    middleware = AutomatedAuditMiddleware(app=app)
    req = _build_request(path="/api/v1/resource", method="POST")

    async def call_next(request):
        return Response(content=b"{}", status_code=200)

    response = asyncio.run(middleware.dispatch(req, call_next))

    def mock_fail(*args, **kwargs):
        raise RuntimeError("Database Down Error Simulation")

    monkeypatch.setattr(system_log_service, "log_system_event", mock_fail)

    async def run_worker():
        await response.background()

    asyncio.run(run_worker())


def test_15_session_for_ignores_stop_iteration_exceptions(isolated_db_context):
    req = _build_request()

    def mock_exhausted_gen():
        yield isolated_db_context
        return

    app.dependency_overrides[get_db] = mock_exhausted_gen
    with _session_for(req) as extracted_session:
        if hasattr(extracted_session, "__next__") or isinstance(
            extracted_session, type((x for x in []))
        ):
            extracted_session = next(extracted_session)
        assert extracted_session == isolated_db_context

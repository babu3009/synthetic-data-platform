from app.main import app
s = app.openapi()
p = s.get("paths", {})
print("task_defaults=", "/api/v1/admin/llm/providers/{provider_id}/task-defaults" in p)
print("audit_recent=", "/api/v1/admin/llm/audit/recent" in p)

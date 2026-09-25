from src.domain.models import TaskPlan

def audit_plan(plan: TaskPlan) -> list[str]:
    """Audit deterministik — pengembalian kosong = lolos."""
    issues: list[str] = []
    conjunctions = (" dan ", " lalu ", " kemudian ")
    
    for s in plan.steps:
        if any(c in s.description.lower() for c in conjunctions):
            issues.append(f"langkah {s.step_id} mungkin multi-aksi")
        if len(s.description) < 8:
            issues.append(f"langkah {s.step_id} terlalu samar")
            
    if len(plan.steps) > 10:
        issues.append(f"{len(plan.steps)} langkah — cek proporsionalitas")
        
    ids = [s.step_id for s in plan.steps]
    if ids != sorted(ids):
        issues.append("step_id tidak monoton")
        
    return issues

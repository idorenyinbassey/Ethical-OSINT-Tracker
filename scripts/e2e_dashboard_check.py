"""Simple script to create a case + investigation and refresh dashboard state."""
from app.repositories.case_repository import create_case
from app.repositories.investigation_repository import create_investigation
from app.repositories.investigation_repository import list_recent, count_all, aggregate_by_day, count_by_kind


def run():
    print('Creating test case...')
    case = create_case(title='E2E Check', description='End-to-end dashboard check', owner_user_id=None)
    print('Case created:', case.id, case.title)
    print('Creating investigation tied to case...')
    inv = create_investigation(kind='test', query='e2e_test_query', result_json='{"status":"ok","risk_score":5}', user_id=None, case_id=case.id)
    print('Investigation created:', inv.id, inv.kind)
    print('Total investigations:', count_all())
    print('Recent investigations:', [ { 'id': inv.id, 'kind': inv.kind, 'query': inv.query } for inv in list_recent(5)])
    print('Counts by kind:', count_by_kind())
    print('Trend last 7 days:', aggregate_by_day(days=7))


if __name__ == '__main__':
    run()

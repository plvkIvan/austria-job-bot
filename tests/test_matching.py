from app.db.models import Job, User
from app.matching.matcher import match_score

def test_city_mismatch():
    assert match_score(User(query='Lager', city='Wien'), Job(source='demo', external_id='1', title='Lager', company='', city='Graz', url='https://example.com')) == 0

def test_matching_title():
    score = match_score(User(query='Lagerarbeiter', city='Wien'), Job(source='demo', external_id='1', title='Lagerarbeiter', company='', city='Wien', url='https://example.com'))
    assert score >= 90

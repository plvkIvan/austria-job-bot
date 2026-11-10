from app.i18n.messages import MESSAGES, t

def test_languages_complete():
    keys = set(MESSAGES['uk'])
    assert all(set(messages) == keys for messages in MESSAGES.values())
    assert 'Stadt' in t('de', 'profile', city='Wien', query='IT', level='B1', employment='-', enabled=True)

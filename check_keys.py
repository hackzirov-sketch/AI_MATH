from database.models import ApiKey, get_session

session = get_session()

keys = session.query(ApiKey).all()
print('Barcha kalitlar:')
for k in keys:
    print('  id=%d, %s, active=%s, usage=%d' % (k.id, k.service, k.is_active, k.usage_count))

dup_count = session.query(ApiKey.service, func.count(ApiKey.id)).group_by(ApiKey.service).having(func.count(ApiKey.id) > 1).all()
print('\nDupikatlar:')
for service, count in dup_count:
    print('  %s: %d marta' % (service, count))
session.close()
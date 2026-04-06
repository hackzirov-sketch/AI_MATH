from database.models import ApiKey, get_session

session = get_session()

# Remove duplicate openrouter (keep the one with less usage)
keys = session.query(ApiKey).filter_by(service='openrouter').all()
print('OpenRouter kalitlari:')
for k in keys:
    print('  id=%d, usage=%d' % (k.id, k.usage_count))

# Keep the one with less usage
if len(keys) > 1:
    to_keep = min(keys, key=lambda x: x.usage_count)
    to_delete = [k for k in keys if k.id != to_keep.id]
    print('\nOchiriladi:')
    for k in to_delete:
        print('  id=%d' % k.id)
        session.delete(k)
    print('\nQoladi:')
    print('  id=%d' % to_keep.id)

session.commit()
session.close()
print('\nBajarildi!')
from services.topic_registry import get_topics_for_grade
from services.ai_generator import _pick_topics_for_type, _normalize_age_group

# Grade 5 uchun mavzular
grade5_topics = get_topics_for_grade(5)
print('=== Grade 5 mavzular (topic_registry) ===')
for topic in grade5_topics:
    print(f'  {topic["title"]}')

print()

# Age group 10-13 uchun mavzular (AI generator)
age_group = '10-13'
ai_topics = _pick_topics_for_type(age_group, 'Matematika', 10)
print('=== Age 10-13 mavzular (AI generator) ===')
print(ai_topics)

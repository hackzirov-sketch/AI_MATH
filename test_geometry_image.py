from services.test_builder import test_builder
from services.test_builder import TestRequest

# Test: 5-sinf, o'rta geometriya - rasm bilan
request = TestRequest(
    subject='geometriya',
    grade=5,
    difficulty='o\'rta',
    question_count=1,
    teacher_name='Test Teacher',
    time_limit=30
)

try:
    response = test_builder.build_test(request)
    print('=== GEOMETRY TEST RESULT ===')
    print(f'Success: {response.success}')
    print(f'Questions: {len(response.questions)}')
    
    if response.questions:
        q = response.questions[0]
        print()
        print('=== QUESTION DETAILS ===')
        print(f'Question: {q.get("question", "No question")}')
        print(f'Topic: {q.get("topic", "No topic")}')
        print(f'Type: {q.get("type", "No type")}')
        print(f'Has image: {q.get("has_image", False)}')
        print(f'Image bytes: {len(q.get("image_bytes", b"")) if q.get("image_bytes") else 0}')
        
        # Geometry hint ni ko'rish
        if 'geometry_hint' in q:
            print(f'Geometry hint: {q["geometry_hint"]}')
        if 'render_spec' in q:
            print(f'Render spec: {q["render_spec"]}')
            
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

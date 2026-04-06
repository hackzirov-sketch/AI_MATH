# Test full render pipeline
from services.test_builder import test_builder
from services.test_builder import TestRequest

request = TestRequest(
    subject='geometriya',
    grade=5,
    difficulty='o\'rta',
    question_count=1,
    teacher_name='Test Teacher',
    time_limit=30,
    topic=None
)

try:
    response = test_builder.build_test(request)
    print('=== FULL GEOMETRY TEST ===')
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
        
        if 'render_spec' in q:
            spec = q['render_spec']
            print(f'Render spec: {spec}')
            
    if response.test_pdf_path:
        print(f'\nTest PDF: {response.test_pdf_path}')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

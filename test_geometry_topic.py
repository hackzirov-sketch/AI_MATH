from services.test_builder import test_builder
from services.test_builder import TestRequest

# Test: 5-sinf, o'rta geometriya
request = TestRequest(
    subject='geometriya',
    grade=5,
    difficulty='o\'rta',
    question_count=2,
    teacher_name='Test Teacher',
    time_limit=30,
    topic='Uchburchak turlari va burchaklari'
)

try:
    response = test_builder.build_test(request)
    print('=== GEOMETRY TEST RESULT ===')
    print(f'Success: {response.success}')
    print(f'Questions: {len(response.questions)}')
    
    if response.questions:
        print()
        print('=== QUESTIONS ===')
        for i, q in enumerate(response.questions, 1):
            print(f'{i}. {q.get("question", "No question")}')
            print(f'   Topic: {q.get("topic", "No topic")}')
            print(f'   Has image: {q.get("has_image", False)}')
            print(f'   Options: {q.get("options", {})}')
            print()
            
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

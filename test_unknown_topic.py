from services.test_builder import test_builder
from services.test_builder import TestRequest

# Test: 5-sinf, o'rta matematika - NOMALUM TOPIC
request = TestRequest(
    subject='matematika',
    grade=5,
    difficulty='o\'rta',
    question_count=3,
    teacher_name='Test Teacher',
    time_limit=30,
    topic=None  # NOMALUM TOPIC
)

try:
    response = test_builder.build_test(request)
    print('=== TEST RESULT (UNKNOWN TOPIC) ===')
    print(f'Success: {response.success}')
    print(f'Questions: {len(response.questions)}')
    print(f'Error: {response.error_message}')
    
    if response.questions:
        print()
        print('=== QUESTIONS ===')
        for i, q in enumerate(response.questions, 1):
            print(f'{i}. {q.get("question", "No question")}')
            print(f'   Topic: {q.get("topic", "No topic")}')
            print(f'   Grade: {q.get("grade", "No grade")}')
            print(f'   Difficulty: {q.get("difficulty", "No difficulty")}')
            print()
            
    if response.test_pdf_path:
        print(f'Test PDF: {response.test_pdf_path}')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

from services.test_builder import test_builder
from services.test_builder import TestRequest

# Real test: 4-sinf, oson matematika
request = TestRequest(
    subject='matematika',
    grade=4,
    difficulty='oson',
    question_count=5,
    teacher_name='Test Teacher',
    time_limit=30
)

try:
    response = test_builder.build_test(request)
    print('=== TEST RESULT ===')
    print(f'Success: {response.success}')
    print(f'Questions: {len(response.questions)}')
    print(f'Answers: {len(response.answers)}')
    print(f'Error: {response.error_message}')
    
    if response.questions:
        print()
        print('=== SAMPLE QUESTIONS ===')
        for i, q in enumerate(response.questions[:3], 1):
            print(f'{i}. {q.get("question", "No question")}')
            print(f'   Options: {q.get("options", {})}')
            print(f'   Correct: {q.get("correct", "No correct")}')
            print()
            
    if response.test_pdf_path:
        print(f'Test PDF: {response.test_pdf_path}')
    if response.answers_pdf_path:
        print(f'Answers PDF: {response.answers_pdf_path}')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

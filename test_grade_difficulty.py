from services.test_builder import test_builder
from services.test_builder import TestRequest

# Test 1: 2-sinf, oson
request1 = TestRequest(
    subject='matematika',
    grade=2,
    difficulty='oson',
    question_count=2,
    teacher_name='Test'
)

# Test 2: 5-sinf, o'rta
request2 = TestRequest(
    subject='matematika',
    grade=5,
    difficulty='o\'rta',
    question_count=2,
    teacher_name='Test'
)

# Test 3: 8-sinf, qiyin
request3 = TestRequest(
    subject='matematika',
    grade=8,
    difficulty='qiyin',
    question_count=2,
    teacher_name='Test'
)

for i, req in enumerate([request1, request2, request3], 1):
    try:
        response = test_builder.build_test(req)
        print(f'Test {i}: Grade {req.grade}, {req.difficulty}')
        print(f'  Success: {response.success}')
        print(f'  Questions: {len(response.questions)}')
        if response.questions:
            q = response.questions[0]
            print(f'  Sample: {q.get("question", "No question")[:80]}...')
        print()
    except Exception as e:
        print(f'Test {i} Error: {e}')
        print()

# Debug: Check if AI questions have render_spec
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
    # Create a proper session
    from services.quiz_uniqueness import QuizUniquenessSession
    session = QuizUniquenessSession()
    
    # Only generate questions, don't render
    questions = test_builder._generate_ai_questions(request, session)
    
    print('=== DEBUG INFO ===')
    print(f'Generated {len(questions)} questions')
    
    for i, q in enumerate(questions, 1):
        print(f'\nQuestion {i}:')
        print(f'  Question: {q.get("question", "No question")[:50]}...')
        print(f'  Topic: {q.get("topic", "No topic")}')
        print(f'  Type: {q.get("type", "No type")}')
        print(f'  Has render_spec: {"render_spec" in q}')
        print(f'  Requires image: {q.get("requires_image", False)}')
        
        if 'render_spec' in q:
            spec = q['render_spec']
            print(f'  Render spec keys: {list(spec.keys())}')
            print(f'  Geometry hint: {spec.get("geometry_hint", "No hint")}')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

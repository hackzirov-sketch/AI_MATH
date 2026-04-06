"""Test the unified puzzle pool generator"""
import sys
import io
import logging
logging.disable(logging.WARNING)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from services.puzzle_pool import puzzle_pool

def test_all():
    categories = ["chain", "grid", "shape", "flowchart"]
    difficulties = ["oson", "o'rta"]
    
    success = 0
    fail = 0
    
    for cat in categories:
        for diff in difficulties:
            try:
                p = puzzle_pool.generate_one(cat, diff, 5, with_diagram=False)
                if p:
                    print(f"[OK] {cat} ({diff}): answer={p.correct_answer}, options={p.options}, correct={p.correct_label}")
                    success += 1
                else:
                    print(f"[SKIP] {cat} ({diff}): no puzzle generated")
                    fail += 1
            except Exception as e:
                print(f"[ERROR] {cat} ({diff}): {e}")
                fail += 1
    
    print()
    print("=== BATCH TEST ===")
    batch = puzzle_pool.generate_batch(5, "o'rta", 5)
    for i, p in enumerate(batch):
        print(f"  {i+1}. [{p.category}] answer={p.correct_answer}, correct_label={p.correct_label}")
    
    print()
    print(f"Results: {success} OK, {fail} failed, {len(batch)} batch")
    print("DONE!")

if __name__ == "__main__":
    test_all()

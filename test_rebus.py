from services.rebus_engine import rebus_engine
r = rebus_engine.generate_symbol_equation(2, "o'rta", 5)
if r:
    print(f"Type: {r.rebus_type}")
    print(f"Display: {r.equation_display}")
    print(f"Answer: {r.correct_answer}")
    print(f"Mapping: {r.symbol_mapping}")
    print(f"Unique: {r.unique_solution}")
else:
    print("No rebus generated - trying chain rebus")
    r = rebus_engine.generate_chain_rebus(3, "o'rta", 5)
    if r:
        print(f"Type: {r.rebus_type}")
        print(f"Display: {r.equation_display}")
        print(f"Answer: {r.correct_answer}")
        print(f"Unique: {r.unique_solution}")
    else:
        print("Chain rebus also failed")

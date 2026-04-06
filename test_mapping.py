# Test grade to age_group mapping
test_cases = [
    (2, 'oson'),
    (2, 'o\'rta'),
    (2, 'qiyin'),
    (5, 'oson'),
    (5, 'o\'rta'),
    (5, 'qiyin'),
    (8, 'oson'),
    (8, 'o\'rta'),
    (8, 'qiyin'),
    (10, 'oson'),
    (10, 'o\'rta'),
    (10, 'qiyin'),
]

for grade, difficulty in test_cases:
    # Grade va difficulty dan age_group yaratish
    if grade <= 4:
        base_age = '6-9'
    elif grade <= 9:
        base_age = '10-13'
    else:
        base_age = '14-17'
    
    if difficulty == 'oson':
        if grade <= 3:
            age_group = '6-9'
        elif grade <= 7:
            age_group = '6-9'
        else:
            age_group = '10-13'
    elif difficulty == 'qiyin':
        if grade <= 6:
            age_group = '10-13'
        else:
            age_group = '14-17'
    else:
        age_group = base_age
    
    print(f'Grade {grade}, {difficulty}: -> Age {age_group}')

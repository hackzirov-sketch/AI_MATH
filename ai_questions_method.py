def _generate_ai_questions(self, request: TestRequest, session: QuizUniquenessSession) -> List[Dict]:
        """AI orqali savollar generatsiya qilish"""
        try:
            from services.ai_generator import run_ai_generation
            from services.key_manager import execute_with_rotation
            
            # Grade va difficulty dan to'g'ri age_group yaratish
            if request.grade <= 4:
                base_age = "6-9"
            elif request.grade <= 9:
                base_age = "10-13"
            else:
                base_age = "14-17"
            
            # Difficulty ga qarab yosh guruhini sozlash
            if request.difficulty.lower() == "oson":
                if request.grade <= 3:
                    age_group = "6-9"
                elif request.grade <= 7:
                    age_group = "6-9"  # Oson uchun pastroq yosh
                else:
                    age_group = "10-13"
            elif request.difficulty.lower() == "qiyin":
                if request.grade <= 6:
                    age_group = "10-13"  # Qiyin uchun yuqoriroq yosh
                else:
                    age_group = "14-17"
            else:  # o'rta
                age_group = base_age
            
            quiz_type = request.subject.capitalize()
            if request.subject.lower() in ["matematika", "algebra"]:
                quiz_type = "Algebra / Matematika"
            
            questions = []
            used_topics = set()
            
            for i in range(request.question_count):
                custom_topic = request.topic
                random_seed = f"test_{request.grade}_{i+1}_{random.randint(1000, 9999)}"
                
                result, error = execute_with_rotation(
                    run_ai_generation,
                    age_group,
                    quiz_type,
                    random_seed,
                    i,
                    1,
                    None,
                    custom_topic
                )
                
                if error:
                    logger.error(f"AI generation error: {error}")
                    continue
                
                if not result or not isinstance(result, dict):
                    logger.error(f"AI returned invalid result: {result}")
                    continue
                
                question_text = result.get("question", "")
                options = result.get("options", [])
                correct_idx = result.get("correct_index", 0)
                explanation = result.get("explanation", "")
                topic = result.get("topic", custom_topic)
                
                if not question_text or len(options) != 4:
                    logger.error(f"Invalid question format: {result}")
                    continue
                
                if correct_idx < len(options):
                    question = {
                        "number": i + 1,
                        "question": question_text,
                        "options": {chr(65 + j): opt for j, opt in enumerate(options)},
                        "correct": chr(65 + correct_idx),
                        "correct_value": options[correct_idx],
                        "explanation": explanation,
                        "topic": topic,
                        "grade": request.grade,
                        "difficulty": request.difficulty,
                        "type": "ai_generated"
                    }
                    
                    # AI savolida geometry_hint bo'lsa, render_spec yaratish
                    geometry_hint = result.get("geometry_hint")
                    if geometry_hint and quiz_type == "Geometriya":
                        question["requires_image"] = True
                        question["render_spec"] = {
                            "question_id": f"ai_{i+1}_{random.randint(1000, 9999)}",
                            "pool_type": "geometry",
                            "topic": topic,
                            "template_id": "ai_geometry",
                            "geometry_hint": geometry_hint,
                            "question_signature": f"ai_geom_{request.grade}_{request.difficulty}"
                        }
                    
                    questions.append(question)
                used_topics.add(topic or custom_topic)
            
            for topic in used_topics:
                session.mark_topic_used(topic)
            
            return questions
            
        except Exception as e:
            logger.error(f"AI questions error: {e}")
            return self._generate_fallback_questions(request, session)

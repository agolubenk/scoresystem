import re
import google.generativeai as genai
from django.conf import settings
from typing import List, Dict, Any

def analyze_interview_results(interview_results: List[Dict]) -> Dict[str, str]:
    """
    Анализирует результаты интервью с помощью Gemini AI и возвращает рекомендации
    """
    # Настройка API ключа
    genai.configure(api_key=settings.GEMINI_API_KEY)
    
    # Подготовка данных для анализа
    results_text = "\n".join([
        f"Параметр: {result['parameter_name']}\n"
        f"Вопрос: {result['question_text']}\n"
        f"Ответ: {result['answer']}\n"
        f"Оценка: {result['score']}\n"
        for result in interview_results
    ])
    
    # Формирование промпта
    prompt = f"""
    Проанализируй результаты интервью и предоставь рекомендации по развитию специалиста.
    Обрати особое внимание на параметры с низкими оценками и предложи конкретные шаги для улучшения.
    
    Результаты интервью:
    {results_text}
    
    Предоставь структурированный ответ в следующем формате:
    1. Общий анализ результатов
    2. Сильные стороны
    3. Области для развития
    4. Конкретные рекомендации по улучшению
    5. Финальное заключение
    """
    
    # Универсальный вызов Gemini AI
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        text = response.text
    except Exception:
        try:
            models = [m.name for m in genai.list_models()]
            for m in models:
                try:
                    model = genai.GenerativeModel(m)
                    response = model.generate_content(prompt)
                    text = response.text
                    break
                except Exception:
                    continue
            else:
                return {
                    'summary': 'Нет данных',
                    'strengths': 'Нет данных',
                    'areas': 'Нет данных',
                    'recommendations': 'Нет данных',
                    'conclusion': 'Нет данных',
                }
        except Exception:
            return {
                'summary': 'Нет данных',
                'strengths': 'Нет данных',
                'areas': 'Нет данных',
                'recommendations': 'Нет данных',
                'conclusion': 'Нет данных',
            }

    # Парсим текст по ключевым словам
    def extract_section(text, start, end=None):
        pattern = rf"\*\*?{re.escape(start)}:?\*\*?(.*?)(?=\*\*?{re.escape(end)}:?\*\*?|$)" if end else rf"\*\*?{re.escape(start)}:?\*\*?(.*)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return 'Нет данных'

    summary = extract_section(text, '1. Общий анализ результатов', '2. Сильные стороны')
    strengths = extract_section(text, '2. Сильные стороны', '3. Области для развития')
    areas = extract_section(text, '3. Области для развития', '4. Конкретные рекомендации по улучшению')
    recommendations = extract_section(text, '4. Конкретные рекомендации по улучшению', '5. Финальное заключение')
    conclusion = extract_section(text, '5. Финальное заключение')

    return {
        'summary': summary,
        'strengths': strengths,
        'areas': areas,
        'recommendations': recommendations,
        'conclusion': conclusion,
    } 
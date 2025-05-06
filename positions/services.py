import google.generativeai as genai
from django.conf import settings
from typing import List, Dict

def analyze_interview_results(interview_results: List[Dict]) -> str:
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
    5. План развития на ближайшие 3 месяца
    """
    
    # Генерация ответа
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)
    
    return response.text 
import google.generativeai as genai
import os

# Configure Gemini if env var is present, otherwise caller must configure
api_key = os.environ.get("SECRET_GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def generate_quotes(keyword: str, count: int = 3) -> list[str]:
    """
    Generates 'count' short inspirational quotes in Spanish based on 'keyword'.
    Returns a list of strings.
    """
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = (
        f"Genera {count} frases inspiradoras y profundas en ESPAÑOL sobre el tema: '{keyword}'. "
        "Cada frase debe ser única, tener un tono motivacional y solemne. "
        "La longitud debe ser de 2 a 4 oraciones cortas (máximo 40 palabras). "
        "NO uses comillas, NO numeres las frases. Simplemente separa cada frase con el símbolo '|||'."
    )

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Split by the separator we asked for
        quotes = [q.strip() for q in text.split('|||') if q.strip()]
        
        # Fallback if Gemini didn't respect the separator
        if len(quotes) < count:
            print(f"Warning: Gemini returned fewer quotes. Raw response: {text}")
            # Try to split by newlines as fallback
            quotes = [q.strip() for q in text.split('\n') if q.strip()]

        return quotes[:count]
    
    except Exception as e:
        print(f"Error creating quotes: {e}")
        return [
            f"El éxito en {keyword} es la suma de pequeños esfuerzos repetidos.",
            f"No esperes a que {keyword} sea fácil, hazte tú más fuerte.",
            f"La verdadera {keyword} nace de la disciplina y el corazón."
        ]

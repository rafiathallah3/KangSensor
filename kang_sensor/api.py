import sys
import warnings

# BUNGKAM PERINGATAN DEPRECATED DARI GOOGLE
warnings.filterwarnings("ignore", category=FutureWarning)

import google.generativeai as genai
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from kang_sensor.config import GEMINI_API_KEY, MODEL_NAME

console = Console()

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

def verify_llm_connection():
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY_HERE":
        raise ValueError("API key has not been configured in 'config.py'. Please set your valid GEMINI_API_KEY.")
    
    # Try fetching model metadata as a lightweight verification check
    model_path = MODEL_NAME if MODEL_NAME.startswith("models/") else f"models/{MODEL_NAME}"
    try:
        genai.get_model(model_path)
    except Exception as e:
        err_msg = str(e)
        if "API key not valid" in err_msg or "API_KEY_INVALID" in err_msg:
            raise ValueError("The configured Gemini API key is invalid.")
        elif "not found" in err_msg.lower() or "not_found" in err_msg.lower() or "404" in err_msg:
            raise ValueError(f"The model name '{MODEL_NAME}' is invalid or could not be found.")
        else:
            raise ConnectionError(f"Failed to connect to Google Generative AI API: {e}")

def call_gemini_api(safe_text: str) -> str:
    system_instruction = """Bertindaklah sebagai asisten AI yang cerdas. 
    ATURAN MUTLAK: Jika terdapat variabel token seperti [REDACTED_...], JANGAN mengubahnya.
    
    Teks Pengguna:
    """
    final_payload = system_instruction + safe_text
    
    # Spinner diubah menjadi tipe "line" agar terkesan seperti proses terminal mentah
    with Progress(SpinnerColumn("line"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("[red][*] Establishing encrypted connection to Gemini...", total=None)
        try:
            response = model.generate_content(final_payload)
            progress.update(task, completed=100)
            return response.text
        except Exception as e:
            progress.stop()
            console.print(f"\n[bold red][-] API Connection Failed: {e}[/bold red]")
            sys.exit(1)

def update_config_api_key(new_key: str):
    import inspect
    import re
    from kang_sensor import config
    
    config_path = inspect.getfile(config)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pattern = r'(GEMINI_API_KEY\s*=\s*)(["\'])(.*?)\2'
    new_content = re.sub(pattern, rf'\g<1>\g<2>{new_key}\g<2>', content)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    # Update in-memory
    config.GEMINI_API_KEY = new_key
    genai.configure(api_key=new_key)
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
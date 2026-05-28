import sys
import warnings
import json
import urllib.request
import urllib.error

# BUNGKAM PERINGATAN DEPRECATED DARI GOOGLE
warnings.filterwarnings("ignore", category=FutureWarning)

import google.generativeai as genai
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from kang_sensor import config

console = Console()

def get_active_provider_config(provider: str = None):
    """
    Returns (provider_name, model_name, api_key) for the selected or default provider.
    """
    # Fallback to default from config
    p = provider.lower() if provider else config.DEFAULT_PROVIDER.lower()
    
    # Valid options
    if p == "gemini":
        return "gemini", config.GEMINI_MODEL, config.GEMINI_API_KEY
    elif p == "openai":
        return "openai", config.OPENAI_MODEL, config.OPENAI_API_KEY
    elif p == "claude":
        return "claude", config.CLAUDE_MODEL, config.CLAUDE_API_KEY
    elif p == "openrouter":
        return "openrouter", config.OPENROUTER_MODEL, config.OPENROUTER_API_KEY
    else:
        raise ValueError(f"Unknown LLM provider: {p}. Choose from: gemini, openai, claude, openrouter")

def update_config_value(variable_name: str, new_value: str):
    """
    Updates a string variable in config.py programmatically.
    """
    import inspect
    import re
    
    config_path = inspect.getfile(config)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Match variable_name = "value" or 'value'
    pattern = rf'({variable_name}\s*=\s*)(["\'])(.*?)\2'
    if re.search(pattern, content):
        new_content = re.sub(pattern, rf'\g<1>\g<2>{new_value}\g<2>', content)
    else:
        # If it doesn't exist, append it at the end
        new_content = content + f'\n{variable_name} = "{new_value}"\n'
        
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    # Update in-memory config object
    setattr(config, variable_name, new_value)

def verify_llm_connection(provider: str = None):
    provider_name, model_name, api_key = get_active_provider_config(provider)
    
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        raise ValueError(f"API key for provider '{provider_name}' has not been configured. Please set a valid key.")
        
    if provider_name == "gemini":
        genai.configure(api_key=api_key)
        model_path = model_name if model_name.startswith("models/") else f"models/{model_name}"
        try:
            genai.get_model(model_path)
        except Exception as e:
            err_msg = str(e)
            if "API key not valid" in err_msg or "API_KEY_INVALID" in err_msg:
                raise ValueError("The configured Gemini API key is invalid.")
            elif "not found" in err_msg.lower() or "not_found" in err_msg.lower() or "404" in err_msg:
                raise ValueError(f"The model name '{model_name}' is invalid or could not be found.")
            else:
                raise ConnectionError(f"Failed to connect to Google Generative AI API: {e}")
    else:
        # For HTTP providers, do a lightweight validation (send a tiny dummy request)
        try:
            _execute_http_request(
                provider_name=provider_name,
                model_name=model_name,
                api_key=api_key,
                prompt="Ping",
                max_tokens=1
            )
        except Exception as e:
            raise ConnectionError(f"Failed to verify connection to {provider_name} API: {e}")

def _execute_http_request(provider_name: str, model_name: str, api_key: str, prompt: str, max_tokens: int = 2000) -> str:
    """
    Executes REST call using urllib.request for OpenAI, Claude, and OpenRouter.
    """
    if provider_name == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": max_tokens
        }
    elif provider_name == "claude":
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": max_tokens
        }
    elif provider_name == "openrouter":
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/rafiathallah3/KangSensor",
            "X-Title": "Kang-Sensor"
        }
        data = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": max_tokens
        }
    else:
        raise ValueError(f"HTTP requests not supported for provider: {provider_name}")

    req_body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            resp_body = response.read().decode("utf-8")
            resp_data = json.loads(resp_body)
            
            if provider_name in ("openai", "openrouter"):
                return resp_data["choices"][0]["message"]["content"]
            elif provider_name == "claude":
                return resp_data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        error_content = e.read().decode("utf-8")
        try:
            error_json = json.loads(error_content)
            if provider_name == "openai" and "error" in error_json:
                msg = error_json["error"].get("message", error_content)
            elif provider_name == "claude" and "error" in error_json:
                msg = error_json["error"].get("message", error_content)
            elif provider_name == "openrouter" and "error" in error_json:
                msg = error_json["error"].get("message", error_content)
            else:
                msg = error_content
        except Exception:
            msg = error_content
        raise ConnectionError(f"HTTP {e.code}: {msg}")
    except Exception as e:
        raise ConnectionError(f"Network error: {e}")

def call_llm_api(safe_text: str, provider: str = None) -> str:
    provider_name, model_name, api_key = get_active_provider_config(provider)
    
    system_instruction = """Bertindaklah sebagai asisten AI yang cerdas. 
    ATURAN MUTLAK: Jika terdapat variabel token seperti [REDACTED_...], JANGAN mengubahnya.
    
    Teks Pengguna:
    """
    final_payload = system_instruction + safe_text
    
    with Progress(SpinnerColumn("line"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task(f"[red][*] Establishing connection to {provider_name.capitalize()} ({model_name})...", total=None)
        try:
            if provider_name == "gemini":
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(final_payload)
                progress.update(task, completed=100)
                return response.text
            else:
                reply = _execute_http_request(
                    provider_name=provider_name,
                    model_name=model_name,
                    api_key=api_key,
                    prompt=final_payload
                )
                progress.update(task, completed=100)
                return reply
        except Exception as e:
            progress.stop()
            console.print(f"\n[bold red][-] API Connection Failed: {e}[/bold red]")
            sys.exit(1)
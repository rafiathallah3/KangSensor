import os
import sys
import re
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from kang_sensor.engine import DataLeakagePreventer
from kang_sensor.api import (
    call_llm_api,
    verify_llm_connection,
    update_config_value,
    get_active_provider_config
)

console = Console()

def run_llm_check(provider: str = None):
    while True:
        try:
            with Progress(SpinnerColumn("line"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                provider_name, _, _ = get_active_provider_config(provider)
                task = progress.add_task(f"[red][*] Checking {provider_name.capitalize()} configuration and connection...", total=None)
                verify_llm_connection(provider)
                progress.update(task, completed=100)
            break
        except Exception as e:
            console.print("\n")
            provider_name, _, _ = get_active_provider_config(provider)
            console.print(Panel(
                f"[bold red][-] {provider_name.capitalize()} Configuration/Connection Failure[/bold red]\n\n"
                f"[red]Error Detail:[/red] {e}\n\n"
                f"[yellow]Please check your API key and model settings for [bold]{provider_name}[/bold] in [bold]kang_sensor/config.py[/bold] or use CLI commands to update them.[/yellow]",
                title="[bold red][ CONNECTION FAILURE ][/bold red]",
                border_style="red",
                box=box.SQUARE
            ))
            
            console.print(f"[bold cyan][?][/bold cyan] Would you like to update your {provider_name.capitalize()} API Key now? (y/n): ", end="")
            try:
                choice = input().strip().lower()
                if choice in ['y', 'yes']:
                    console.print("[bold cyan][?][/bold cyan] Enter new API Key: ", end="")
                    new_key = input().strip()
                    if new_key:
                        var_name = f"{provider_name.upper()}_API_KEY"
                        update_config_value(var_name, new_key)
                        console.print("[bold green][+] Config updated. Retrying connection check...[/bold green]")
                        continue
                    else:
                        console.print("[bold yellow][!] Empty key entered. Aborting...[/bold yellow]")
                else:
                    console.print("[bold red][!] Aborted by user.[/bold red]")
            except (KeyboardInterrupt, EOFError):
                console.print("\n[bold red][!] Aborted.[/bold red]")
            
            sys.exit(1)

def run_interactive_mode(preventer: DataLeakagePreventer, provider: str = None):
    provider_name, model_name, _ = get_active_provider_config(provider)
    console.print(Panel(
        f"[bold red]KANG-SENSOR DLP v1.0[/bold red]\n"
        f"[dim]Mode: Interactive Multi-Turn Payload Scanner[/dim]\n"
        f"[dim]Uplink: {provider_name.capitalize()} ({model_name})[/dim]\n"
        f"[dim]Press [bold yellow]Ctrl+C[/bold yellow] at any time to exit.[/dim]",
        border_style="red",
        box=box.SQUARE
    ))

    while True:
        try:
            console.print(Panel(
                "[bold cyan]INPUT PAYLOAD[/bold cyan]\n"
                "[dim]Enter your payload or raw text below. Type 'PROSES' on a new line and press Enter to scan & execute.[/dim]",
                border_style="cyan",
                box=box.SQUARE
            ))
            
            lines = []
            while True:
                line = input()
                if line.strip().upper() == 'PROSES':
                    break
                lines.append(line)
                
            user_input = "\n".join(lines)
            if not user_input.strip():
                console.print("[bold yellow][!] Warning: Empty payload. Please try again.[/bold yellow]")
                continue

            current_preventer = DataLeakagePreventer()

            with Progress(SpinnerColumn("line"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                task1 = progress.add_task("[red][*] Scanning and redacting local payload...", total=None)
                safe_text = current_preventer.anonymize(user_input, source_name="interactive_terminal")
                progress.update(task1, completed=100)

            current_preventer.print_dashboard()
            current_preventer.export_audit_log()
            console.print("[dim][+] Audit log dumped to 'audit_trail.json'[/dim]")
            
            console.print("\n[bold red][*] SANITIZED PAYLOAD:[/bold red]")
            console.print(Panel(safe_text, border_style="dim", box=box.SQUARE))

            console.print("\n[bold red][*] Initiating secure AI uplink...[/bold red]")
            llm_reply = call_llm_api(safe_text, provider=provider)

            with Progress(SpinnerColumn("line"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                task3 = progress.add_task("[green][*] Restoring original tokens...", total=None)
                final_output = current_preventer.deanonymize(llm_reply)
                progress.update(task3, completed=100)

            console.print("\n")
            console.print(Panel(final_output, title="[bold green][ EXECUTION COMPLETE ][/bold green]", border_style="green", box=box.SQUARE))

        except (KeyboardInterrupt, EOFError):
            console.print("\n\n[bold red][!] Interrupted. Exiting Kang-Sensor DLP. Stay safe![/bold red]\n")
            break


def run_file_mode(preventer: DataLeakagePreventer, input_file: str, output_file: str, ai_fix: bool, provider: str = None):
    if not os.path.exists(input_file):
        console.print(f"[bold red][-] Target not found: {input_file}[/bold red]")
        sys.exit(1)

    provider_name, model_name, _ = get_active_provider_config(provider)
    console.print(Panel(
        f"[bold red]KANG-SENSOR DLP v1.0[/bold red]\n"
        f"[dim]Target: {input_file}[/dim]\n"
        f"[dim]Uplink: {provider_name.capitalize()} ({model_name})[/dim]",
        border_style="red",
        box=box.SQUARE
    ))
    
    with open(input_file, 'r', encoding='utf-8') as f:
        user_input = f.read()

    with Progress(SpinnerColumn("line"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task1 = progress.add_task(f"[red][*] Deep scanning {input_file}...", total=None)
        safe_text = preventer.anonymize(user_input, source_name=input_file)
        progress.update(task1, completed=100)

    preventer.print_dashboard()
    preventer.export_audit_log()
    console.print("[dim][+] Audit log dumped to 'audit_trail.json'[/dim]")

    if ai_fix:
        console.print("\n[bold red][*] Requesting AI remediation...[/bold red]")
        
        # PROMPT INJECTION
        prompt = (
            "Perbaiki HANYA kesalahan sintaksis, eror struktur, atau typo pada teks/kode/konfigurasi berikut. "
            "WAJIB letakkan seluruh hasil perbaikan di dalam blok kode Markdown (```). "
            "ATURAN SANGAT KRITIS (JIKA DILANGGAR SISTEM AKAN HANCUR): "
            "1. DILARANG mengubah nama key/variabel (contoh: jangan ubah 'nama_lengkap' menjadi 'namalengkap'). "
            "2. DILARANG menciptakan kata sensor buatanmu sendiri (seperti REDACTEDCUSTOMER_NAME atau SENSITIVEDATA_HIDDEN). "
            "3. COPY-PASTE secara persis dan utuh semua token [REDACTED_...] ke dalam blok kodemu tanpa mengubah satu karakter pun. "
            "ATURAN OUTPUT: Berikan maksimal satu baris kalimat pengantar saja di luar blok kode:\n\n" + safe_text
        )
        llm_reply = call_llm_api(prompt, provider=provider)
        
        # 1. DEANONYMIZE UTUH: Mengembalikan token menjadi kredensial asli untuk seluruh teks (termasuk basa-basi AI)
        with Progress(SpinnerColumn("line"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task3 = progress.add_task("[green][*] Restoring original tokens...", total=None)
            full_restored_text = preventer.deanonymize(llm_reply)
            progress.update(task3, completed=100)
            
        # 2. TAMPILAN CLI: Menampilkan output utuh (beserta kalimat pengantar) di terminal
        console.print("\n")
        console.print(Panel(full_restored_text, title="[bold green][ AI REMEDIATION RESPONSE ][/bold green]", border_style="green", box=box.SQUARE))

        # 3. EKSTRAKSI FILE: Membuang kalimat pengantar hanya untuk disimpan ke file
        saved_text = full_restored_text
        if not input_file.lower().endswith('.txt'):
            batas_kode = chr(96) + chr(96) + chr(96) # Menghasilkan ```
            if batas_kode in full_restored_text:
                potongan = full_restored_text.split(batas_kode)
                if len(potongan) >= 3:
                    isi_kode = potongan[1]
                    garis_baru_pertama = isi_kode.find('\n')
                    if garis_baru_pertama != -1:
                        saved_text = isi_kode[garis_baru_pertama+1:].strip() + "\n"
                    else:
                        saved_text = isi_kode.strip() + "\n"
        
        # 4. In-Place Overwrite
        out_path = output_file if output_file else input_file
        action_msg = "Target overwritten in-place"

    else:
        # Mode Scan-Only tetap membuat file kloningan agar file aslinya tidak rusak/hilang data
        saved_text = safe_text
        out_path = output_file if output_file else f"safe_{os.path.basename(input_file)}"
        action_msg = "Output saved to"

    # Menyimpan teks (yang sudah dibersihkan basa-basinya) ke file
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(saved_text)

    console.print(f"\n[bold green][+] Operation successful. {action_msg}: {out_path}[/bold green]")


def main():
    parser = argparse.ArgumentParser(description="Kang-Sensor: Tactical Data Leakage Prevention (DLP) Tool.")
    parser.add_argument("-i", "--input", help="Target file to scan (Optional)")
    parser.add_argument("-o", "--output", help="Output destination (Optional)")
    parser.add_argument("--scan-only", action="store_true", help="Local scan & redact only (File mode)")
    parser.add_argument("--ai-fix", action="store_true", help="Scan, send to AI, and restore in-place (File mode)")
    parser.add_argument("-p", "--provider", help="Select LLM provider for this run (gemini, openai, claude, openrouter)")
    parser.add_argument("--set-provider", help="Set default LLM provider permanently (gemini, openai, claude, openrouter)")
    parser.add_argument("--set-key", help="Update API Key for the selected provider (or default provider if not specified)")
    parser.add_argument("--set-model", help="Update default model name for the selected provider (or default provider if not specified)")
    
    args = parser.parse_args()
    console.clear()

    # 1. Handle --set-provider
    if args.set_provider:
        prov = args.set_provider.lower()
        valid_providers = ["gemini", "openai", "claude", "openrouter"]
        if prov not in valid_providers:
            console.print(f"[bold red][-] Error: Invalid provider. Choose from: {', '.join(valid_providers)}[/bold red]")
            sys.exit(1)
        try:
            update_config_value("DEFAULT_PROVIDER", prov)
            console.print(Panel(
                f"[bold green][+] Default LLM provider successfully updated![/bold green]\n\n"
                f"[dim]New Default Provider: {prov}[/dim]",
                title="[bold green][ CONFIG UPDATED ][/bold green]",
                border_style="green",
                box=box.SQUARE
            ))
            sys.exit(0)
        except Exception as e:
            console.print(f"[bold red][-] Failed to update provider config: {e}[/bold red]")
            sys.exit(1)

    # Resolve target provider for actions
    target_provider = args.provider if args.provider else None

    # 2. Handle --set-key
    if args.set_key:
        try:
            provider_name, _, _ = get_active_provider_config(target_provider)
            var_name = f"{provider_name.upper()}_API_KEY"
            update_config_value(var_name, args.set_key)
            console.print(Panel(
                f"[bold green][+] API Key for {provider_name.upper()} successfully updated in config![/bold green]\n\n"
                f"[dim]New Key: {args.set_key[:6]}...{args.set_key[-4:] if len(args.set_key) > 10 else args.set_key}[/dim]",
                title="[bold green][ CONFIG UPDATED ][/bold green]",
                border_style="green",
                box=box.SQUARE
            ))
            sys.exit(0)
        except Exception as e:
            console.print(f"[bold red][-] Failed to update API key: {e}[/bold red]")
            sys.exit(1)

    # 3. Handle --set-model
    if args.set_model:
        try:
            provider_name, _, _ = get_active_provider_config(target_provider)
            var_name = f"{provider_name.upper()}_MODEL"
            update_config_value(var_name, args.set_model)
            console.print(Panel(
                f"[bold green][+] Model for {provider_name.upper()} successfully updated in config![/bold green]\n\n"
                f"[dim]New Model: {args.set_model}[/dim]",
                title="[bold green][ CONFIG UPDATED ][/bold green]",
                border_style="green",
                box=box.SQUARE
            ))
            sys.exit(0)
        except Exception as e:
            console.print(f"[bold red][-] Failed to update model config: {e}[/bold red]")
            sys.exit(1)

    preventer = DataLeakagePreventer()

    if args.input:
        if args.scan_only and args.ai_fix:
            console.print("[bold red][-] Conflict: Use either --scan-only OR --ai-fix, not both.[/bold red]")
            sys.exit(1)
        if args.ai_fix:
            run_llm_check(provider=target_provider)
        run_file_mode(preventer, args.input, args.output, ai_fix=args.ai_fix, provider=target_provider)
    else:
        if args.scan_only or args.ai_fix:
            console.print("[bold red][-] Error: Flags --scan-only and --ai-fix require an input file (-i).[/bold red]")
            sys.exit(1)
        run_llm_check(provider=target_provider)
        run_interactive_mode(preventer, provider=target_provider)

if __name__ == "__main__":
    main()
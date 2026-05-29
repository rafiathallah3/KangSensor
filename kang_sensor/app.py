import os
import sys
import re
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False

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

def redraw_menu(prompt: str, input_str: str, filtered_cmds: list, selected_idx: int, menu_height_printed: int) -> int:
    # 1. Clear previous menu lines
    if menu_height_printed > 0:
        for _ in range(menu_height_printed):
            sys.stdout.write("\033[B") # Move cursor down
            sys.stdout.write("\r\033[K") # Clear line
        sys.stdout.write(f"\033[{menu_height_printed}A") # Move back up
        sys.stdout.write("\r")
        sys.stdout.flush()

    # 2. Print input line
    sys.stdout.write("\r\033[K")
    console.print(f"[bold red]{prompt}[/bold red]{input_str}", end="")
    sys.stdout.flush()

    # 3. Print autocomplete dropdown
    new_menu_height = 0
    if filtered_cmds and input_str.startswith('/'):
        new_menu_height = len(filtered_cmds)
        for idx, cmd in enumerate(filtered_cmds):
            sys.stdout.write("\n")
            if idx == selected_idx:
                console.print(f"  [bold red]>[/bold red] [red]{cmd}[/red]", end="")
            else:
                console.print(f"    [dim]{cmd}[/dim]", end="")
        
        # Move cursor back up to input line
        sys.stdout.write(f"\033[{new_menu_height}A")
        sys.stdout.write("\r")
        console.print(f"[bold red]{prompt}[/bold red]{input_str}", end="")
        sys.stdout.flush()
        
    return new_menu_height

def get_intellisense_input(prompt: str, commands: list) -> str:
    if not HAS_MSVCRT or not sys.stdin.isatty():
        console.print(f"[bold red]{prompt}[/bold red]", end="")
        return input()

    input_str = ""
    selected_idx = 0
    menu_height_printed = 0
    
    # Initial draw
    menu_height_printed = redraw_menu(prompt, input_str, [], 0, 0)
    
    while True:
        # Get filtered commands
        filtered_cmds = []
        if input_str.startswith('/'):
            filtered_cmds = [c for c in commands if c.startswith(input_str.lower())]
            if selected_idx >= len(filtered_cmds):
                selected_idx = 0
        else:
            selected_idx = 0
            
        # Redraw screen and menu
        menu_height_printed = redraw_menu(prompt, input_str, filtered_cmds, selected_idx, menu_height_printed)
        
        try:
            ch = msvcrt.getch()
        except KeyboardInterrupt:
            clear_menu_lines(menu_height_printed)
            raise KeyboardInterrupt
            
        if ch in (b'\x00', b'\xe0'):
            # Special key
            try:
                ch2 = msvcrt.getch()
            except KeyboardInterrupt:
                clear_menu_lines(menu_height_printed)
                raise KeyboardInterrupt
                
            if ch2 == b'H': # Up arrow
                if filtered_cmds:
                    selected_idx = (selected_idx - 1) % len(filtered_cmds)
            elif ch2 == b'P': # Down arrow
                if filtered_cmds:
                    selected_idx = (selected_idx + 1) % len(filtered_cmds)
            continue
            
        if ch in (b'\r', b'\n'):
            # Enter
            if filtered_cmds and input_str.startswith('/'):
                input_str = filtered_cmds[selected_idx]
            clear_menu_lines(menu_height_printed)
            print() # Advance terminal cursor
            return input_str
            
        elif ch == b'\x08':
            # Backspace
            if len(input_str) > 0:
                input_str = input_str[:-1]
                selected_idx = 0
                
        elif ch == b'\t':
            # Tab autocompletes
            if filtered_cmds and input_str.startswith('/'):
                input_str = filtered_cmds[selected_idx] + " "
                selected_idx = 0
                
        elif ch == b'\x03':
            # Ctrl+C
            clear_menu_lines(menu_height_printed)
            raise KeyboardInterrupt
            
        elif ch == b'\x1a':
            # Ctrl+Z
            clear_menu_lines(menu_height_printed)
            raise EOFError
            
        else:
            try:
                char_str = ch.decode('utf-8', errors='ignore')
                if char_str:
                    input_str += char_str
                    selected_idx = 0
            except Exception:
                pass

def clear_menu_lines(menu_height: int):
    if menu_height > 0:
        for _ in range(menu_height):
            sys.stdout.write("\033[B")
            sys.stdout.write("\r\033[K")
        sys.stdout.write(f"\033[{menu_height}A")
        sys.stdout.write("\r")
        sys.stdout.flush()

def run_interactive_mode(preventer: DataLeakagePreventer, provider: str = None):
    active_provider = provider
    provider_name, model_name, _ = get_active_provider_config(active_provider)
    console.print(Panel(
        f"[bold red]KANG-SENSOR DLP v1.0[/bold red]\n"
        f"[dim]Mode: Interactive Tactical Payload Scanner[/dim]\n"
        f"[dim]Uplink: {provider_name.capitalize()} ({model_name})[/dim]\n"
        f"[dim]Press [bold yellow]Ctrl+C[/bold yellow] at any time to exit.[/dim]\n"
        f"[dim]Type [bold yellow]/help[/bold yellow] or [bold yellow]/[/bold yellow] to see available commands.[/dim]",
        border_style="red",
        box=box.SQUARE
    ))

    while True:
        try:
            provider_name, model_name, _ = get_active_provider_config(active_provider)
            # Display premium command line prompt with Intellisense
            line = get_intellisense_input(
                prompt="kang-sensor > ",
                commands=['/help', '/provider', '/model', '/status', '/paste', '/clear', '/exit', '/quit']
            ).strip()
            
            if not line:
                continue

            # Command Handling
            if line.startswith('/'):
                cmd_parts = line.split(maxsplit=1)
                cmd = cmd_parts[0].lower()
                cmd_arg = cmd_parts[1].strip() if len(cmd_parts) > 1 else ""

                if cmd in ('/', '/help', '/?'):
                    console.print(Panel(
                        "[bold red]AVAILABLE COMMANDS[/bold red]\n\n"
                        "  [bold yellow]/help[/bold yellow], [bold yellow]/[/bold yellow]      - Show this command navigation menu\n"
                        "  [bold yellow]/provider[/bold yellow]  - Switch LLM provider (Gemini, Claude, Codex, OpenRouter) and update key\n"
                        "  [bold yellow]/model[/bold yellow]     - Update default model name for the active provider\n"
                        "  [bold yellow]/status[/bold yellow]    - Show current connection and active LLM configuration details\n"
                        "  [bold yellow]/paste[/bold yellow]     - Enter multi-line paste mode (type 'PROSES' on a new line to submit)\n"
                        "  [bold yellow]/clear[/bold yellow]     - Clear the terminal screen\n"
                        "  [bold yellow]/exit[/bold yellow], [bold yellow]/quit[/bold yellow] - Exit interactive mode",
                        title="[bold red][ MENU ][/bold red]",
                        border_style="red",
                        box=box.SQUARE
                    ))
                    continue

                elif cmd == '/provider':
                    console.print(Panel(
                        "[bold cyan]SELECT LLM PROVIDER[/bold cyan]\n\n"
                        "  [1] Gemini\n"
                        "  [2] Claude\n"
                        "  [3] Codex (OpenAI)\n"
                        "  [4] OpenRouter",
                        border_style="cyan",
                        box=box.SQUARE
                    ))
                    console.print("[bold cyan][?][/bold cyan] Enter choice (1-4 or provider name): ", end="")
                    choice = input().strip().lower()
                    
                    provider_map = {
                        '1': ('gemini', 'Gemini'),
                        'gemini': ('gemini', 'Gemini'),
                        '2': ('claude', 'Claude'),
                        'claude': ('claude', 'Claude'),
                        '3': ('openai', 'Codex (OpenAI)'),
                        'codex': ('openai', 'Codex (OpenAI)'),
                        'openai': ('openai', 'Codex (OpenAI)'),
                        '4': ('openrouter', 'OpenRouter'),
                        'openrouter': ('openrouter', 'OpenRouter')
                    }
                    
                    if choice not in provider_map:
                        console.print("[bold red][-] Error: Invalid choice. Action cancelled.[/bold red]")
                        continue
                        
                    chosen_provider, chosen_display = provider_map[choice]
                    console.print(f"[bold cyan][?][/bold cyan] Enter API Token for {chosen_display}: ", end="")
                    new_token = input().strip()
                    if not new_token:
                        console.print("[bold yellow][!] Warning: Empty token entered. Action cancelled.[/bold yellow]")
                        continue
                        
                    # Update config
                    var_name = f"{chosen_provider.upper()}_API_KEY"
                    update_config_value(var_name, new_token)
                    update_config_value("DEFAULT_PROVIDER", chosen_provider)
                    active_provider = chosen_provider
                    
                    # Verify connection
                    with Progress(SpinnerColumn("line"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                        task = progress.add_task(f"[red][*] Establishing connection to {chosen_display}...", total=None)
                        try:
                            verify_llm_connection(active_provider)
                            progress.update(task, completed=100)
                            console.print(f"[bold green][+] Connection established successfully to {chosen_display}![/bold green]")
                        except Exception as e:
                            progress.stop()
                            console.print(Panel(
                                f"[bold red][-] Connection Verification Failure[/bold red]\n\n"
                                f"[red]Error Detail:[/red] {e}\n\n"
                                f"[yellow]Your key is saved, but connection failed. Please check your credentials.[/yellow]",
                                border_style="red",
                                box=box.SQUARE
                            ))
                    continue

                elif cmd == '/model':
                    _, current_model, _ = get_active_provider_config(active_provider)
                    console.print(f"[bold cyan][+] Active Model:[/bold cyan] {current_model}")
                    console.print(f"[bold cyan][?][/bold cyan] Enter new model name (or press Enter to keep current): ", end="")
                    new_model = input().strip()
                    if new_model:
                        var_name = f"{provider_name.upper()}_MODEL"
                        update_config_value(var_name, new_model)
                        console.print(f"[bold green][+] Model updated to {new_model}[/bold green]")
                    else:
                        console.print("[dim][+] Kept current model.[/dim]")
                    continue

                elif cmd == '/status':
                    _, current_model, api_key = get_active_provider_config(active_provider)
                    console.print(Panel(
                        f"[bold red]KANG-SENSOR SECURITY GATEWAY STATUS[/bold red]\n\n"
                        f"[bold]Active Uplink:[/bold] {provider_name.capitalize()}\n"
                        f"[bold]Active Model:[/bold] {current_model}\n"
                        f"[bold]API Key status:[/bold] {'[green]CONFIGURED[/green]' if api_key and api_key != 'YOUR_API_KEY_HERE' else '[red]NOT CONFIGURED[/red]'}",
                        border_style="red",
                        box=box.SQUARE
                    ))
                    # Test connection
                    with Progress(SpinnerColumn("line"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                        task = progress.add_task(f"[red][*] Testing connection uplink...", total=None)
                        try:
                            verify_llm_connection(active_provider)
                            progress.update(task, completed=100)
                            console.print("[bold green][+] Connection: ONLINE[/bold green]")
                        except Exception as e:
                            progress.stop()
                            console.print(f"[bold red][-] Connection: OFFLINE ({e})[/bold red]")
                    continue

                elif cmd == '/clear':
                    console.clear()
                    continue

                elif cmd in ('/exit', '/quit'):
                    console.print("\n[bold red][!] Exiting Kang-Sensor DLP. Stay safe![/bold red]\n")
                    break

                elif cmd == '/paste':
                    console.print(Panel(
                        "[bold cyan]PASTE MODE[/bold cyan]\n"
                        "[dim]Paste your multi-line payload below. Type 'PROSES' on a new line and press Enter to finish.[/dim]",
                        border_style="cyan",
                        box=box.SQUARE
                    ))
                    paste_lines = []
                    while True:
                        paste_line = input()
                        if paste_line.strip().upper() == 'PROSES':
                            break
                        paste_lines.append(paste_line)
                    user_input = "\n".join(paste_lines)
                else:
                    console.print(f"[bold red][-] Unknown command: {cmd}. Type /help for available commands.[/bold red]")
                    continue
            else:
                # Normal single-line or backslash continuation input
                lines = [line]
                while line.endswith('\\'):
                    # remove trailing backslash
                    lines[-1] = lines[-1][:-1]
                    console.print("[dim]> [/dim]", end="")
                    line = input()
                    lines.append(line)
                user_input = "\n".join(lines)

            # Execution logic
            if not user_input.strip():
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
            try:
                llm_reply = call_llm_api(safe_text, provider=active_provider)
            except Exception as e:
                console.print(Panel(
                    f"[bold red][-] AI Uplink Connection Failed[/bold red]\n\n"
                    f"[red]Error Detail:[/red] {e}\n\n"
                    f"[yellow]Your local data remains redacted. Please check your credentials or run [bold]/provider[/bold] to update them.[/yellow]",
                    title="[bold red][ UPLINK FAILURE ][/bold red]",
                    border_style="red",
                    box=box.SQUARE
                ))
                continue

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
        try:
            llm_reply = call_llm_api(prompt, provider=provider)
        except Exception as e:
            console.print(f"\n[bold red][-] AI Remediation Failed: {e}[/bold red]")
            sys.exit(1)
        
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
        # Check connection status at interactive startup but do not fail hard
        provider_name, _, _ = get_active_provider_config(target_provider)
        try:
            with Progress(SpinnerColumn("line"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                task = progress.add_task(f"[red][*] Checking {provider_name.capitalize()} configuration and connection...", total=None)
                verify_llm_connection(target_provider)
                progress.update(task, completed=100)
            console.print(f"[bold green][+] Connected successfully to {provider_name.capitalize()}![/bold green]")
        except Exception as e:
            console.print(Panel(
                f"[bold red][-] {provider_name.capitalize()} Configuration/Connection Warning[/bold red]\n\n"
                f"[red]Warning Detail:[/red] {e}\n\n"
                f"[yellow]The current LLM API key is invalid or unconfigured. You can still scan local files, or type [bold]/provider[/bold] in the terminal to configure it.[/yellow]",
                title="[bold red][ CONNECTION WARNING ][/bold red]",
                border_style="red",
                box=box.SQUARE
            ))
        
        run_interactive_mode(preventer, provider=target_provider)

if __name__ == "__main__":
    main()
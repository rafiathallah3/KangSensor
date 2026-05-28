import os
import sys
import re
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from kang_sensor.engine import DataLeakagePreventer
from kang_sensor.api import call_gemini_api

console = Console()

def run_interactive_mode(preventer: DataLeakagePreventer):
    console.print(Panel("[bold red]KANG-SENSOR DLP v1.0[/bold red]\n[dim]Mode: Interactive Payload Scanner[/dim]", border_style="red", box=box.SQUARE))
    console.print("\n[bold red][?][/bold red] Enter payload or raw text below.")
    console.print("[dim](Type 'PROSES' on a new line and press Enter to execute)[/dim]")
    
    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == 'PROSES':
                break
            lines.append(line)
        except EOFError:
            break
            
    user_input = "\n".join(lines)
    if not user_input.strip():
        console.print("[bold red][-] Execution aborted: Empty payload.[/bold red]")
        return

    with Progress(SpinnerColumn("line"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task1 = progress.add_task("[red][*] Scanning and redacting local payload...", total=None)
        safe_text = preventer.anonymize(user_input, source_name="interactive_terminal")
        progress.update(task1, completed=100)

    preventer.print_dashboard()
    preventer.export_audit_log()
    console.print("[dim][+] Audit log dumped to 'audit_trail.json'[/dim]")
    
    console.print("\n[bold red][*] SANITIZED PAYLOAD:[/bold red]")
    console.print(Panel(safe_text, border_style="dim", box=box.SQUARE))

    console.print("\n[bold red][*] Initiating secure AI uplink...[/bold red]")
    llm_reply = call_gemini_api(safe_text)

    with Progress(SpinnerColumn("line"), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task3 = progress.add_task("[green][*] Restoring original tokens...", total=None)
        final_output = preventer.deanonymize(llm_reply)
        progress.update(task3, completed=100)

    console.print("\n")
    console.print(Panel(final_output, title="[bold green][ EXECUTION COMPLETE ][/bold green]", border_style="green", box=box.SQUARE))


def run_file_mode(preventer: DataLeakagePreventer, input_file: str, output_file: str, ai_fix: bool):
    if not os.path.exists(input_file):
        console.print(f"[bold red][-] Target not found: {input_file}[/bold red]")
        sys.exit(1)

    console.print(Panel(f"[bold red]KANG-SENSOR DLP v1.0[/bold red]\n[dim]Target: {input_file}[/dim]", border_style="red", box=box.SQUARE))
    
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
            "Perbaiki kode/teks berikut. Untuk kode pemrograman, WAJIB letakkan "
            "seluruh kode hasil perbaikan di dalam blok kode Markdown (```). "
            "Jangan mengubah atau menghilangkan token [REDACTED_...]:\n\n" + safe_text
        )
        llm_reply = call_gemini_api(prompt)
        
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
    
    args = parser.parse_args()
    console.clear()

    preventer = DataLeakagePreventer()

    if args.input:
        if args.scan_only and args.ai_fix:
            console.print("[bold red][-] Conflict: Use either --scan-only OR --ai-fix, not both.[/bold red]")
            sys.exit(1)
        run_file_mode(preventer, args.input, args.output, ai_fix=args.ai_fix)
    else:
        if args.scan_only or args.ai_fix:
            console.print("[bold red][-] Error: Flags --scan-only and --ai-fix require an input file (-i).[/bold red]")
            sys.exit(1)
        run_interactive_mode(preventer)

if __name__ == "__main__":
    main()
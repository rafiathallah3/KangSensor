import time
import json
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich import box

from kang_sensor.patterns import SENSITIVE_PATTERNS, RISK_WEIGHTS
from kang_sensor.config import AUDIT_LOG_FILE

console = Console()

class DataLeakagePreventer:
    def __init__(self):
        self.vault = {}
        self.token_counter = 0
        self.audit_log = []
        self.total_risk_score = 0
        self.scan_time = 0

    def calculate_risk_level(self):
        if self.total_risk_score >= 100: return "[bold red][ FATAL ][/bold red]"
        elif self.total_risk_score >= 50: return "[bold bright_red][ HIGH ][/bold bright_red]"
        elif self.total_risk_score >= 20: return "[bold yellow][ MED ][/bold yellow]"
        elif self.total_risk_score > 0: return "[bold green][ LOW ][/bold green]"
        return "[dim white][ SAFE ][/dim white]"

    def anonymize(self, text: str, source_name: str = "interactive_terminal") -> str:
        anonymized_text = text
        start_time = time.time()

        for entity_type, pattern in SENSITIVE_PATTERNS.items():
            for match in pattern.finditer(anonymized_text):
                actual_match = match.group(1) if match.lastindex else match.group(0)
                actual_match = actual_match.strip()
                
                if not actual_match: continue
                
                if actual_match not in self.vault.values():
                    self.token_counter += 1
                    token = f"[REDACTED_{entity_type}_{self.token_counter}]"
                    self.vault[token] = actual_match
                    
                    risk_points = RISK_WEIGHTS.get(entity_type, 10)
                    self.total_risk_score += risk_points
                    
                    self.audit_log.append({
                        "timestamp": datetime.now().isoformat(),
                        "source": source_name,
                        "entity_type": entity_type,
                        "token_id": token,
                        "risk_points": risk_points
                    })
                else:
                    token = [k for k, v in self.vault.items() if v == actual_match][0]
                
                anonymized_text = anonymized_text.replace(actual_match, token)
        
        self.scan_time = (time.time() - start_time) * 1000
        return anonymized_text

    def deanonymize(self, text: str) -> str:
        deanonymized_text = text
        for token, original_value in self.vault.items():
            deanonymized_text = deanonymized_text.replace(token, original_value)
        return deanonymized_text

    def export_audit_log(self):
        if self.audit_log:
            with open(AUDIT_LOG_FILE, 'w') as f:
                json.dump({
                    "scan_metadata": {
                        "total_entities_redacted": self.token_counter,
                        "cumulative_risk_score": self.total_risk_score,
                        "scan_duration_ms": round(self.scan_time, 2)
                    },
                    "events": self.audit_log
                }, f, indent=4)

    def print_dashboard(self):
        if self.vault:
            # Desain Tabel Red Team (Kotak kaku, warna merah/putih)
            table = Table(title="[bold red]KANG-SENSOR: THREAT METRICS[/bold red]", style="red", box=box.SQUARE)
            table.add_column("Metric", justify="left", style="dim white", no_wrap=True)
            table.add_column("Value", justify="right", style="bold red")
            
            table.add_row("Entities Intercepted", f"{self.token_counter}")
            table.add_row("Threat Level", self.calculate_risk_level())
            table.add_row("Cumulative Risk", f"{self.total_risk_score}")
            table.add_row("Execution Time", f"{self.scan_time:.2f} ms")
            console.print(table)

            console.print("\n[bold red][!] LOCAL VAULT (Redacted Data):[/bold red]")
            for token, original in self.vault.items():
                console.print(f"  [+] {token} -> [dim]{original}[/dim]")
        else:
            console.print("\n[bold green][+] TARGET CLEAN. 0 ms - NO SENSITIVE DATA DETECTED.[/bold green]")
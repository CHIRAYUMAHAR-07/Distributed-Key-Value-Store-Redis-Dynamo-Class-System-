"""
Command Line Interface for KV Store
"""
import asyncio
import argparse
import json
import sys
from typing import Optional, List, Dict, Any
from tabulate import tabulate
from colorama import init, Fore, Style

from .client import KVClient, ClientConfig, SyncKVClient

init(autoreset=True)  # Initialize colorama

class KVStoreCLI:
    """Interactive CLI for KV Store"""
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.client = None
        self.prompt = f"{Fore.GREEN}kvstore>{Style.RESET_ALL} "
    
    def connect(self):
        """Connect to cluster"""
        config = ClientConfig(
            coordinator_host=self.host,
            coordinator_port=self.port
        )
        self.client = SyncKVClient(config)
        self.client.__enter__()
        
        # Test connection
        status = self.client.get_cluster_status()
        if "error" in status:
            print(f"{Fore.RED}Error connecting to coordinator: {status['error']}{Style.RESET_ALL}")
            return False
        
        print(f"{Fore.GREEN}Connected to cluster at {self.host}:{self.port}{Style.RESET_ALL}")
        print(f"Cluster status: {status.get('total_nodes', 0)} nodes online")
        return True
    
    def disconnect(self):
        """Disconnect from cluster"""
        if self.client:
            self.client.__exit__(None, None, None)
            self.client = None
            print(f"{Fore.YELLOW}Disconnected{Style.RESET_ALL}")
    
    def run_interactive(self):
        """Run interactive CLI"""
        if not self.connect():
            return
        
        print(f"\n{Fore.CYAN}Distributed KV Store CLI{Style.RESET_ALL}")
        print("Commands: get, set, delete, exists, incr, stats, nodes, exit")
        print("Type 'help' for more information\n")
        
        while True:
            try:
                command = input(self.prompt).strip()
                if not command:
                    continue
                
                if command.lower() == "exit":
                    break
                elif command.lower() == "help":
                    self._show_help()
                else:
                    self._execute_command(command)
                    
            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        
        self.disconnect()
    
    def _show_help(self):
        """Show help message"""
        help_text = """
Available Commands:
  get <key>                    - Get value for key
  set <key> <value> [ttl]      - Set key-value pair with optional TTL
  delete <key>                 - Delete key
  exists <key>                 - Check if key exists
  incr <key> [amount]          - Increment numeric value
  batch_get <key1> <key2> ...  - Get multiple keys
  batch_set <json>             - Set multiple keys from JSON
  stats                        - Show cluster statistics
  nodes                        - Show node status
  monitor                      - Monitor cluster in real-time
  help                         - Show this help
  exit                         - Exit CLI
        """
        print(help_text)
    
    def _execute_command(self, command: str):
        """Execute a CLI command"""
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == "get":
            if len(args) < 1:
                print("Usage: get <key>")
                return
            value = self.client.get(args[0])
            if value is not None:
                print(f"{Fore.GREEN}{args[0]}: {value}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}Key not found{Style.RESET_ALL}")
        
        elif cmd == "set":
            if len(args) < 2:
                print("Usage: set <key> <value> [ttl]")
                return
            key = args[0]
            value = " ".join(args[1:-1]) if len(args) > 2 else args[1]
            ttl = int(args[-1]) if args[-1].isdigit() and len(args) > 2 else None
            
            # Try to parse JSON
            try:
                value = json.loads(value)
            except:
                pass
            
            success = self.client.set(key, value, ttl)
            if success:
                print(f"{Fore.GREEN}OK{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Failed{Style.RESET_ALL}")
        
        elif cmd == "delete":
            if len(args) < 1:
                print("Usage: delete <key>")
                return
            success = self.client.delete(args[0])
            if success:
                print(f"{Fore.GREEN}Deleted{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Failed{Style.RESET_ALL}")
        
        elif cmd == "exists":
            if len(args) < 1:
                print("Usage: exists <key>")
                return
            exists = self.client.exists(args[0])
            print(f"{Fore.GREEN if exists else Fore.RED}{exists}{Style.RESET_ALL}")
        
        elif cmd == "incr":
            if len(args) < 1:
                print("Usage: incr <key> [amount]")
                return
            amount = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
            result = self.client.increment(args[0], amount)
            if result is not None:
                print(f"{Fore.GREEN}{args[0]}: {result}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Failed{Style.RESET_ALL}")
        
        elif cmd == "stats":
            status = self.client.get_cluster_status()
            if "error" in status:
                print(f"{Fore.RED}Error: {status['error']}{Style.RESET_ALL}")
                return
            
            stats = status.get("stats", {})
            table = [
                ["Total Requests", stats.get("total_requests", 0)],
                ["Successful", stats.get("successful_requests", 0)],
                ["Failed", stats.get("failed_requests", 0)],
                ["Avg Latency", f"{stats.get('avg_latency', 0):.3f}s"],
                ["Online Nodes", stats.get("nodes_online", 0)]
            ]
            
            print(tabulate(table, headers=["Metric", "Value"], tablefmt="grid"))
        
        elif cmd == "nodes":
            status = self.client.get_cluster_status()
            if "error" in status:
                print(f"{Fore.RED}Error: {status['error']}{Style.RESET_ALL}")
                return
            
            nodes = status.get("nodes", [])
            if not nodes:
                print(f"{Fore.YELLOW}No nodes found{Style.RESET_ALL}")
                return
            
            table_data = []
            for node in nodes:
                status_color = Fore.GREEN if node.get("is_alive") else Fore.RED
                status_text = f"{status_color}{'ALIVE' if node.get('is_alive') else 'DEAD'}{Style.RESET_ALL}"
                table_data.append([
                    node.get("id", "?"),
                    f"{node.get('host')}:{node.get('port')}",
                    status_text,
                    node.get("virtual_nodes", 0)
                ])
            
            headers = ["Node ID", "Address", "Status", "Virtual Nodes"]
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
        
        elif cmd == "monitor":
            self._monitor_cluster()
        
        elif cmd == "batch_get":
            if len(args) < 1:
                print("Usage: batch_get <key1> <key2> ...")
                return
            
            # This would need async implementation
            print(f"{Fore.YELLOW}Batch operations require async client{Style.RESET_ALL}")
        
        elif cmd == "batch_set":
            if len(args) < 1:
                print("Usage: batch_set '{\"key1\": \"value1\", \"key2\": \"value2\"}'")
                return
            
            try:
                items = json.loads(" ".join(args))
                if not isinstance(items, dict):
                    raise ValueError("Input must be a JSON object")
                
                # This would need async implementation
                print(f"{Fore.YELLOW}Batch operations require async client{Style.RESET_ALL}")
                
            except json.JSONDecodeError:
                print(f"{Fore.RED}Invalid JSON{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        
        else:
            print(f"{Fore.RED}Unknown command: {cmd}{Style.RESET_ALL}")
            print("Type 'help' for available commands")
    
    def _monitor_cluster(self):
        """Monitor cluster in real-time"""
        try:
            import time
            
            print(f"{Fore.CYAN}Monitoring cluster (Ctrl+C to stop)...{Style.RESET_ALL}")
            print("-" * 50)
            
            previous_stats = {}
            while True:
                status = self.client.get_cluster_status()
                
                if "error" not in status:
                    stats = status.get("stats", {})
                    nodes = status.get("nodes", [])
                    
                    # Clear screen (simple approach)
                    print("\033[H\033[J", end="")
                    
                    # Header
                    print(f"{Fore.CYAN}Cluster Monitor - {time.strftime('%H:%M:%S')}{Style.RESET_ALL}")
                    print("-" * 50)
                    
                    # Stats
                    table = [
                        ["Requests/sec", stats.get("total_requests", 0) - previous_stats.get("total_requests", 0)],
                        ["Total Nodes", len(nodes)],
                        ["Alive Nodes", sum(1 for n in nodes if n.get("is_alive"))],
                        ["Avg Latency", f"{stats.get('avg_latency', 0):.3f}s"]
                    ]
                    print(tabulate(table, headers=["Metric", "Value"], tablefmt="simple"))
                    print()
                    
                    # Nodes
                    print(f"{Fore.YELLOW}Nodes:{Style.RESET_ALL}")
                    for node in nodes:
                        status_icon = "🟢" if node.get("is_alive") else "🔴"
                        print(f"  {status_icon} {node.get('id')} - {node.get('host')}:{node.get('port')}")
                    
                    previous_stats = stats.copy()
                
                time.sleep(2)  # Update every 2 seconds
                
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Monitoring stopped{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Monitor error: {e}{Style.RESET_ALL}")

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Distributed KV Store CLI")
    parser.add_argument("--host", default="localhost", help="Coordinator host")
    parser.add_argument("--port", type=int, default=8080, help="Coordinator port")
    parser.add_argument("--command", help="Command to execute (non-interactive)")
    
    args = parser.parse_args()
    
    cli = KVStoreCLI(host=args.host, port=args.port)
    
    if args.command:
        # Non-interactive mode
        if cli.connect():
            cli._execute_command(args.command)
            cli.disconnect()
    else:
        # Interactive mode
        cli.run_interactive()

if __name__ == "__main__":
    main()
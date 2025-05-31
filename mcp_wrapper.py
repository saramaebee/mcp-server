#!/usr/bin/env python3
"""
MCP Server Wrapper with Watchdog File Monitoring

This wrapper manages the actual MCP server as a subprocess and restarts it
when source files change, while maintaining a stable connection to the MCP client.
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class MCPServerManager:
    def __init__(self, server_command, watch_dirs, watch_files):
        self.server_command = server_command
        self.watch_dirs = watch_dirs
        self.watch_files = watch_files
        self.server_process = None
        self.observer = None
        self.restart_requested = False
        self.last_restart = 0
        self.restart_delay = 1.0  # Minimum seconds between restarts
        
    def start_server(self):
        """Start the MCP server subprocess."""
        if self.server_process and self.server_process.poll() is None:
            return  # Already running
            
        print(f"🚀 Starting MCP server: {' '.join(self.server_command)}", file=sys.stderr)
        
        try:
            self.server_process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0  # Unbuffered for real-time communication
            )
            print(f"📍 Server started with PID: {self.server_process.pid}", file=sys.stderr)
        except Exception as e:
            print(f"❌ Failed to start server: {e}", file=sys.stderr)
            sys.exit(1)
    
    def stop_server(self):
        """Stop the MCP server subprocess."""
        if self.server_process and self.server_process.poll() is None:
            print(f"🛑 Stopping server (PID: {self.server_process.pid})", file=sys.stderr)
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("⚠️  Server didn't stop gracefully, killing...", file=sys.stderr)
                self.server_process.kill()
                self.server_process.wait()
            self.server_process = None
    
    def restart_server(self):
        """Restart the MCP server subprocess."""
        current_time = time.time()
        if current_time - self.last_restart < self.restart_delay:
            return  # Too soon to restart
            
        self.last_restart = current_time
        print("🔄 Restarting MCP server...", file=sys.stderr)
        self.stop_server()
        time.sleep(0.5)  # Brief pause
        self.start_server()
        print("✅ Server restarted", file=sys.stderr)
    
    def setup_file_watcher(self):
        """Set up file watching with watchdog."""
        class RestartHandler(FileSystemEventHandler):
            def __init__(self, manager):
                self.manager = manager
                
            def on_modified(self, event):
                if event.is_directory:
                    return
                    
                # Only watch Python files and pyproject.toml
                if not (event.src_path.endswith('.py') or event.src_path.endswith('pyproject.toml')):
                    return
                    
                print(f"🔄 File changed: {event.src_path}", file=sys.stderr)
                self.manager.restart_server()
        
        self.observer = Observer()
        handler = RestartHandler(self)
        
        # Watch directories
        for watch_dir in self.watch_dirs:
            if watch_dir.exists():
                self.observer.schedule(handler, str(watch_dir), recursive=True)
                print(f"📁 Watching directory: {watch_dir}", file=sys.stderr)
        
        # Watch specific files by watching their parent directories
        for watch_file in self.watch_files:
            if watch_file.exists():
                self.observer.schedule(handler, str(watch_file.parent), recursive=False)
                print(f"📄 Watching file: {watch_file}", file=sys.stderr)
        
        self.observer.start()
        print("👀 File watcher started", file=sys.stderr)
    
    def forward_io(self):
        """Forward stdin/stdout between client and server subprocess."""
        def forward_stdin():
            """Forward stdin from client to server."""
            try:
                while self.server_process and self.server_process.poll() is None:
                    line = sys.stdin.readline()
                    if not line:
                        break
                    if self.server_process and self.server_process.stdin:
                        self.server_process.stdin.write(line)
                        self.server_process.stdin.flush()
            except Exception as e:
                print(f"stdin forwarding error: {e}", file=sys.stderr)
        
        def forward_stdout():
            """Forward stdout from server to client."""
            try:
                while self.server_process and self.server_process.poll() is None:
                    if self.server_process and self.server_process.stdout:
                        line = self.server_process.stdout.readline()
                        if not line:
                            break
                        sys.stdout.write(line)
                        sys.stdout.flush()
            except Exception as e:
                print(f"stdout forwarding error: {e}", file=sys.stderr)
        
        def forward_stderr():
            """Forward stderr from server to our stderr."""
            try:
                while self.server_process and self.server_process.poll() is None:
                    if self.server_process and self.server_process.stderr:
                        line = self.server_process.stderr.readline()
                        if not line:
                            break
                        print(f"[SERVER] {line.rstrip()}", file=sys.stderr)
            except Exception as e:
                print(f"stderr forwarding error: {e}", file=sys.stderr)
        
        # Start forwarding threads
        stdin_thread = threading.Thread(target=forward_stdin, daemon=True)
        stdout_thread = threading.Thread(target=forward_stdout, daemon=True)
        stderr_thread = threading.Thread(target=forward_stderr, daemon=True)
        
        stdin_thread.start()
        stdout_thread.start()
        stderr_thread.start()
        
        return stdin_thread, stdout_thread, stderr_thread
    
    def run(self):
        """Main run loop."""
        # Set up signal handlers
        def signal_handler(signum, frame):
            print("🧹 Shutting down...", file=sys.stderr)
            self.stop_server()
            if self.observer:
                self.observer.stop()
                self.observer.join()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Start file watcher
            self.setup_file_watcher()
            
            # Start server
            self.start_server()
            
            # Set up IO forwarding
            threads = self.forward_io()
            
            print("✨ MCP wrapper ready! Server will auto-reload when files change.", file=sys.stderr)
            
            # Wait for server process
            while True:
                if self.server_process:
                    exit_code = self.server_process.poll()
                    if exit_code is not None:
                        print(f"⚠️  Server exited with code {exit_code}", file=sys.stderr)
                        # Don't auto-restart if it was an intentional shutdown
                        if exit_code != 0:
                            time.sleep(1)
                            self.start_server()
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None)


def main():
    """Main entry point."""
    # Configuration
    server_dir = Path(__file__).parent
    server_command = [
        "/Users/sara/.local/bin/uv", "run", "devrev-mcp"
    ]
    
    watch_dirs = [server_dir / "src"]
    watch_files = [server_dir / "pyproject.toml"]
    
    # Enable debug mode
    os.environ["DRMCP_DEBUG"] = "1"
    
    print("🔄 Starting MCP Server Wrapper with Python watchdog", file=sys.stderr)
    print("🐛 Debug mode: ENABLED", file=sys.stderr)
    print("", file=sys.stderr)
    
    # Create and run manager
    manager = MCPServerManager(server_command, watch_dirs, watch_files)
    manager.run()


if __name__ == "__main__":
    main()
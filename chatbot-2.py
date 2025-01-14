import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import os
import subprocess
import threading
import psutil
from typing import Dict, Optional
import ttkthemes

class ServerProcess(threading.Thread):
    def __init__(self, server_type: str, command: str, output_callback):
        super().__init__()
        self.server_type = server_type
        self.command = command
        self.process: Optional[subprocess.Popen] = None
        self.running = False
        self.output_callback = output_callback

    def run(self):
        try:
            self.process = subprocess.Popen(
                self.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            self.running = True
            
            while self.running and self.process.poll() is None:
                output = self.process.stdout.readline()
                if output:
                    self.output_callback(f"[{self.server_type}] {output.strip()}")
        except Exception as e:
            self.output_callback(f"[{self.server_type}] Error: {str(e)}")

    def stop(self):
        self.running = False
        if self.process:
            try:
                for child in psutil.Process(self.process.pid).children(recursive=True):
                    child.terminate()
                self.process.terminate()
                self.process.wait()
            except:
                pass

class InstagramChatbotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Instagram Chatbot Manager")
        self.root.geometry("1000x800")
        
        # Apply modern theme
        self.style = ttkthemes.ThemedStyle(self.root)
        self.style.set_theme("arc")
        
        # Initialize server processes
        self.server_processes: Dict[str, Optional[ServerProcess]] = {
            'flask': None,
            'node': None,
            'ngrok': None,
            'ngrok_config': None,
            'llama' : None
        }
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status bar at the top
        self.status_var = tk.StringVar(value="Status: Ready")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, font=('Helvetica', 10))
        status_label.pack(fill=tk.X, pady=(0, 20))

        # Create notebook for tabbed interface
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Configuration tab
        config_frame = ttk.Frame(notebook, padding="10")
        notebook.add(config_frame, text="Configuration")

        # Ngrok Configuration Section
        ngrok_frame = ttk.LabelFrame(config_frame, text="Ngrok Configuration", padding="10")
        ngrok_frame.pack(fill=tk.X, pady=(0, 10))

        self.ngrok_fields = {}
        ngrok_labels = ['NGROK_TOKEN', 'NGROK_URL']
        
        for label in ngrok_labels:
            frame = ttk.Frame(ngrok_frame)
            frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(frame, text=f"{label}:", width=15).pack(side=tk.LEFT)
            entry = ttk.Entry(frame)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
            self.ngrok_fields[label] = entry

        ttk.Button(ngrok_frame, text="Configure Ngrok Token", 
                  command=self.configure_ngrok).pack(pady=(10, 0))

        # Instagram API Configuration Section
        api_frame = ttk.LabelFrame(config_frame, text="Instagram API Configuration", padding="10")
        api_frame.pack(fill=tk.X, pady=10)

        self.config_fields = {}
        api_labels = ['VERIFY_TOKEN', 'APP_SECRET', 'ACCESS_TOKEN', 'IG_ID']
        
        for label in api_labels:
            frame = ttk.Frame(api_frame)
            frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(frame, text=f"{label}:", width=15).pack(side=tk.LEFT)
            entry = ttk.Entry(frame)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
            self.config_fields[label] = entry

        # Configuration buttons
        btn_frame = ttk.Frame(api_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="Load Configuration", 
                  command=self.load_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Save Configuration", 
                  command=self.save_config).pack(side=tk.LEFT)

        # Server Control Section
        control_frame = ttk.LabelFrame(main_frame, text="Server Control", padding="10")
        control_frame.pack(fill=tk.X, pady=10)

        self.start_btn = ttk.Button(control_frame, text="Start Servers", 
                                  command=self.start_servers)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = ttk.Button(control_frame, text="Stop Servers", 
                                 command=self.stop_servers, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)

        # Log Output Section
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.log_output = scrolledtext.ScrolledText(log_frame, height=10, 
                                                  wrap=tk.WORD, font=('Courier', 9))
        self.log_output.pack(fill=tk.BOTH, expand=True)

    def configure_ngrok(self):
        token = self.ngrok_fields['NGROK_TOKEN'].get().strip()
        if not token:
            self.show_error("Please enter the Ngrok authtoken")
            return
            
        command = f'ngrok config add-authtoken {token}'
        self.server_processes['ngrok_config'] = ServerProcess(
            'ngrok_config', command, self.update_log)
        self.server_processes['ngrok_config'].start()
        self.update_log("Configuring ngrok token...")
        self.status_var.set("Status: Configuring Ngrok...")

    def load_config(self):
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    config = json.load(f)
                    for key, value in config.items():
                        if key in self.config_fields:
                            self.config_fields[key].delete(0, tk.END)
                            self.config_fields[key].insert(0, value)
                        elif key in self.ngrok_fields:
                            self.ngrok_fields[key].delete(0, tk.END)
                            self.ngrok_fields[key].insert(0, value)
                self.update_log("Configuration loaded successfully")
                self.status_var.set("Status: Configuration loaded")
        except Exception as e:
            self.show_error(f"Error loading configuration: {str(e)}")

    def save_config(self):
        try:
            config = {}
            for key, field in {**self.config_fields, **self.ngrok_fields}.items():
                value = field.get().strip()
                if value:
                    config[key] = value
            
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=4)
            
            with open('.env', 'w') as f:
                for key, value in config.items():
                    f.write(f"{key}=\"{value}\"\n")
                    
            self.update_log("Configuration saved successfully")
            self.status_var.set("Status: Configuration saved")
        except Exception as e:
            self.show_error(f"Error saving configuration: {str(e)}")


    def llama (self):
        self.update_log("Checking if ollama is downloaded or not... ")
        result = subprocess.run(['pip', 'show', 'ollama'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text = True)
        if result.returncode == 0:
            self.update_log("ollama is already installed")
        else:
            self.update_log("Ollama not found. Installing ollama...")
            result = subprocess.run(['pip', 'install', 'ollama'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text = True)
            if result.returncode == 0:
                self.update_log("ollama installed successfully")
            else:
                self.update_log("Error installing ollama")
                return
            
        self.update_log("Starting ollama...")
        self.update_log("Checking if the model is downloaded or not...")
        result = subprocess.run(
            ["ollama", "list"], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if "llama3.2:latest" not in result.stdout:
            self.update_log("Model not found. Downloading the model")
            result = subprocess.run(
                ["ollama", "pull", "llama3.2:latest"], 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if result.returncode == 0:
                self.update_log("Model downloaded successfully")
            else:
                self.update_log("Error downloading the model")
                return
            
        self.update_log("Model is downloaded. Starting ollama...")
        self.server_processes['llama'] = ServerProcess(
            'llama', 'ollama serve', self.update_log)
        
        self.server_processes['llama'].start()


    def start_servers(self):
        try:
            token = self.ngrok_fields['NGROK_TOKEN'].get().strip()
            ngrok_url = self.ngrok_fields['NGROK_URL'].get().strip()
            
            if not token or not ngrok_url:
                self.show_error("Please configure Ngrok token and URL first")
                return
            # Start ollama
            self.llama()
            # Start Flask server
            self.server_processes['flask'] = ServerProcess(
                'flask', 'python model2.py', self.update_log)
            self.server_processes['flask'].start()
            
            # Start Node.js server
            self.server_processes['node'] = ServerProcess(
                'node', 'node server2.js', self.update_log)
            self.server_processes['node'].start()
            
            # Start ngrok
            ngrok_command = f'ngrok http --url={ngrok_url} 69'
            self.server_processes['ngrok'] = ServerProcess(
                'ngrok', ngrok_command, self.update_log)
            self.server_processes['ngrok'].start()

            self.start_btn.configure(state=tk.DISABLED)
            self.stop_btn.configure(state=tk.NORMAL)
            self.status_var.set("Status: Servers running")
            
        except Exception as e:
            self.show_error(f"Error starting servers: {str(e)}")

    def stop_servers(self):
        try:
            for server_type, process in self.server_processes.items():
                if process and process.running:
                    process.stop()
                    process.join()
                    self.update_log(f"{server_type} server stopped")
                self.server_processes[server_type] = None

            self.start_btn.configure(state=tk.NORMAL)
            self.stop_btn.configure(state=tk.DISABLED)
            self.update_log("All servers stopped")
            self.status_var.set("Status: Servers stopped")
            
        except Exception as e:
            self.show_error(f"Error stopping servers: {str(e)}")

    def update_log(self, message):
        self.log_output.insert(tk.END, f"{message}\n")
        self.log_output.see(tk.END)

    def show_error(self, message):
        messagebox.showerror("Error", message)

if __name__ == '__main__':
    root = tk.Tk()
    app = InstagramChatbotGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.stop_servers)
    root.mainloop()
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os
import requests
import json
import webbrowser
from threading import Thread
import time

class InstallerWizard:
    def __init__(self, root):
        self.root = root
        self.root.title("Instagram Chatbot Installer")
        self.root.geometry("800x600")
        
        # Main container
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self.main_frame, variable=self.progress_var, maximum=100)
        self.progress.pack(fill=tk.X, pady=(0, 20))
        
        # Status label
        self.status_var = tk.StringVar(value="Welcome to the Instagram Chatbot Installer")
        self.status_label = ttk.Label(self.main_frame, textvariable=self.status_var)
        self.status_label.pack(pady=(0, 20))
        
        # Content frame
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Initialize steps
        self.current_step = 0
        self.steps = [
            self.install_ollama,
            self.download_llama_model,
            self.setup_ngrok,
            self.setup_facebook,
            self.finalize_setup
        ]
        
        # Start button
        self.next_button = ttk.Button(self.main_frame, text="Start Installation", command=self.next_step)
        self.next_button.pack(pady=20)
        
        # Config storage
        self.config = {}

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def install_ollama(self):
        self.clear_content()
        self.status_var.set("Step 1: Installing Ollama")
        self.progress_var.set(0)
        
        def download_ollama():
            try:
                # Download Ollama installer
                url = "https://ollama.com/download/windows"
                response = requests.get(url, stream=True)
                total_size = int(response.headers.get('content-length', 0))
                
                filename = "ollama-installer.exe"
                block_size = 1024
                downloaded = 0
                
                with open(filename, 'wb') as f:
                    for data in response.iter_content(block_size):
                        downloaded += len(data)
                        f.write(data)
                        progress = (downloaded / total_size) * 100
                        self.progress_var.set(progress)
                
                # Run installer
                subprocess.run([filename], check=True)
                os.remove(filename)
                
                self.status_var.set("Ollama installed successfully")
                self.next_button.config(state=tk.NORMAL, text="Next")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to install Ollama: {str(e)}")
                self.next_button.config(state=tk.NORMAL)
        
        self.next_button.config(state=tk.DISABLED)
        Thread(target=download_ollama).start()

    def download_llama_model(self):
        self.clear_content()
        self.status_var.set("Step 2: Downloading LLaMA Model")
        self.progress_var.set(25)
        
        def download_model():
            try:
                # Execute ollama pull command
                process = subprocess.Popen(
                    ["ollama", "pull", "llama3.2:latest"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        self.status_var.set(output.strip())
                
                self.status_var.set("LLaMA model downloaded successfully")
                self.next_button.config(state=tk.NORMAL)
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to download model: {str(e)}")
                self.next_button.config(state=tk.NORMAL)
        
        self.next_button.config(state=tk.DISABLED)
        Thread(target=download_model).start()

    def setup_ngrok(self):
        self.clear_content()
        self.status_var.set("Step 3: Ngrok Configuration")
        self.progress_var.set(50)
        
        ttk.Label(self.content_frame, text="1. Create an Ngrok account at:").pack()
        link = ttk.Label(self.content_frame, text="https://ngrok.com", foreground="blue", cursor="hand2")
        link.pack()
        link.bind("<Button-1>", lambda e: webbrowser.open("https://ngrok.com"))
        
        ttk.Label(self.content_frame, text="\n2. Get your Ngrok auth token from:").pack()
        token_link = ttk.Label(self.content_frame, text="https://dashboard.ngrok.com/get-started/your-authtoken", 
                             foreground="blue", cursor="hand2")
        token_link.pack()
        token_link.bind("<Button-1>", 
                       lambda e: webbrowser.open("https://dashboard.ngrok.com/get-started/your-authtoken"))
        
        token_frame = ttk.Frame(self.content_frame)
        token_frame.pack(pady=20)
        ttk.Label(token_frame, text="Auth Token:").pack(side=tk.LEFT)
        self.token_entry = ttk.Entry(token_frame, width=40)
        self.token_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(self.content_frame, text="\n3. Create a static domain at:").pack()
        domain_link = ttk.Label(self.content_frame, text="https://dashboard.ngrok.com/cloud-edge/domains", 
                              foreground="blue", cursor="hand2")
        domain_link.pack()
        domain_link.bind("<Button-1>", 
                        lambda e: webbrowser.open("https://dashboard.ngrok.com/cloud-edge/domains"))
        
        domain_frame = ttk.Frame(self.content_frame)
        domain_frame.pack(pady=20)
        ttk.Label(domain_frame, text="Static Domain:").pack(side=tk.LEFT)
        self.domain_entry = ttk.Entry(domain_frame, width=40)
        self.domain_entry.pack(side=tk.LEFT, padx=5)
        
        self.next_button.config(command=lambda: self.save_ngrok_config())

    def save_ngrok_config(self):
        token = self.token_entry.get().strip()
        domain = self.domain_entry.get().strip()
        
        if not token or not domain:
            messagebox.showerror("Error", "Please fill in both fields")
            return
            
        self.config['NGROK_TOKEN'] = token
        self.config['NGROK_URL'] = domain
        self.next_step()

    def setup_facebook(self):
        self.clear_content()
        self.status_var.set("Step 4: Facebook App Configuration")
        self.progress_var.set(75)
        
        ttk.Label(self.content_frame, text="1. Create a Facebook App at:").pack()
        link = ttk.Label(self.content_frame, text="https://developers.facebook.com/apps/", 
                        foreground="blue", cursor="hand2")
        link.pack()
        link.bind("<Button-1>", lambda e: webbrowser.open("https://developers.facebook.com/apps/"))
        
        # Create entry fields
        fields = ['VERIFY_TOKEN', 'APP_SECRET', 'ACCESS_TOKEN', 'IG_ID']
        self.fb_entries = {}
        
        for field in fields:
            frame = ttk.Frame(self.content_frame)
            frame.pack(pady=10)
            ttk.Label(frame, text=f"{field}:").pack(side=tk.LEFT)
            entry = ttk.Entry(frame, width=40)
            entry.pack(side=tk.LEFT, padx=5)
            self.fb_entries[field] = entry
        
        self.next_button.config(command=lambda: self.save_facebook_config())

    def save_facebook_config(self):
        for key, entry in self.fb_entries.items():
            value = entry.get().strip()
            if not value:
                messagebox.showerror("Error", f"Please fill in {key}")
                return
            self.config[key] = value
        
        # Save all configuration
        with open('config.json', 'w') as f:
            json.dump(self.config, f, indent=4)
            
        with open('.env', 'w') as f:
            for key, value in self.config.items():
                f.write(f"{key}=\"{value}\"\n")
        
        self.next_step()

    def finalize_setup(self):
        self.clear_content()
        self.status_var.set("Installation Complete!")
        self.progress_var.set(100)
        
        ttk.Label(self.content_frame, text="All components have been installed and configured successfully!").pack(pady=20)
        ttk.Label(self.content_frame, text="To start the chatbot:").pack()
        ttk.Label(self.content_frame, text="1. Run chatbot-2.exe").pack()
        ttk.Label(self.content_frame, text="2. Click 'Start Servers' in the interface").pack()
        
        self.next_button.config(text="Finish", command=self.root.destroy)

    def next_step(self):
        if self.current_step < len(self.steps):
            self.steps[self.current_step]()
            self.current_step += 1

if __name__ == "__main__":
    root = tk.Tk()
    app = InstallerWizard(root)
    root.mainloop()
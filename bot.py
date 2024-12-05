import subprocess, configparser, os, threading, json, re, asyncio, socket, subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime, timedelta
try:
    import psutil
except ModuleNotFoundError:
    subprocess.run(["pip3", "install", "psutil"])
    import psutil
try:
    import discord
except ModuleNotFoundError:
    subprocess.run(["pip3", "install", "discord.py"])
    import discord
from discord.ext import commands
try:
    import requests
except ModuleNotFoundError:
    subprocess.run(["pip3", "install", "requests"])


class ModeSelector:
    def __init__(self, master):
        self.master = master
        master.title("Render Farm Bot - Mode Selection")
        
        ttk.Button(master, text="Start as Server", command=self.start_server).pack(pady=10)
        ttk.Button(master, text="Start as Client", command=self.start_client).pack(pady=10)
    
    def start_server(self):
        self.master.destroy()
        root = tk.Tk()
        ServerApp(root)
        root.mainloop()
    
    def start_client(self):
        self.master.destroy()
        root = tk.Tk()
        ClientApp(root)
        root.mainloop()

class ServerApp:
    def __init__(self, master):
        self.master = master
        master.title("Render Farm Bot - Server")
        
        self.clients = []
        self.server_socket = None
        
        ttk.Button(master, text="Start Server", command=self.start_server).pack(pady=10)
        self.client_listbox = tk.Listbox(master)
        self.client_listbox.pack(pady=10)
        
        ttk.Button(master, text="Manage Selected Client", command=self.manage_client).pack(pady=10)
    
    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('0.0.0.0', 36745))
        self.server_socket.listen(5)
        
        threading.Thread(target=self.accept_clients, daemon=True).start()
    
    def accept_clients(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            self.clients.append(client_socket)
            self.client_listbox.insert(tk.END, f"Client {addr}")
            threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
    
    def manage_client(self):
        selected = self.client_listbox.curselection()
        if selected:
            client_socket = self.clients[selected[0]]

class ClientApp:
    def __init__(self, master):
        self.master = master
        master.title("Render Farm Bot - Client")
        
        ttk.Label(master, text="Server IP:").pack(pady=5)
        self.server_ip = ttk.Entry(master)
        self.server_ip.pack(pady=5)
        
        ttk.Button(master, text="Connect to Server", command=self.connect_to_server).pack(pady=10)
    
    def connect_to_server(self):
        ip = self.server_ip.get()
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((ip, 36745))
            messagebox.showinfo("Success", "Connected to server")
            self.start_render_farm_bot()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect: {str(e)}")
    
    def start_render_farm_bot(self):
        self.master.destroy()
        root = tk.Tk()
        RenderFarmBot(root, self.client_socket)
        root.mainloop()

class ComputeDevice:
    def __init__(self, name, gpu_id):
        self.using_default = tk.BooleanVar(value=True)
        self.name = name
        self.gpu_id = gpu_id
        self.enabled = tk.BooleanVar(value=False)
        self.login = tk.StringVar()
        self.password = tk.StringVar()
        self.cores = tk.IntVar(value=1)
        self.memory = tk.DoubleVar(value=1)
        self.custom_args = tk.StringVar()
        self.process = None
        self.log_text = None
        self.auto_restart = tk.BooleanVar(value=True)
        self.verbose = tk.BooleanVar(value=False)
        self.headless = tk.BooleanVar(value=False)
        self.sandbox = tk.BooleanVar(value=False)
        self.disable_large_downloads = tk.BooleanVar(value=False)
        self.start_on_manager_start = tk.BooleanVar(value=False)
        self.status = "OFF"
        self.frame = None
        self.command_display = None
        self.status_label = None
        self.cache_dir = tk.StringVar()
        self.proxy = tk.StringVar()
        self.max_rendertime = tk.IntVar(value=0)
        self.current_job = ""
        self.progress = 0
        self.points_generated = 0
        self.time_running = timedelta()
        self.downloads = 0
        self.uploads = 0
        self.start_time = None
        self.closing = False
        self.status_lock = threading.Lock()
        self.client_name = tk.StringVar()  # New field
        self.priority = tk.IntVar(value=0)

class RenderFarmBot:
    def __init__(self, master):
        self.master = master
        master.title("Render Farm Bot")
        
        self.notebook = ttk.Notebook(master)
        self.main_tab = ttk.Frame(self.notebook)
        self.devices_tab = ttk.Frame(self.notebook)
        self.log_tab = ttk.Frame(self.notebook)
        self.discord_tab = ttk.Frame(self.notebook)
        self.config_tab = ttk.Frame(self.notebook)
        self.network_tab = ttk.Frame(self.notebook)  # New network tab
        
        self.notebook.add(self.main_tab, text="Main")
        self.notebook.add(self.devices_tab, text="Devices")
        self.notebook.add(self.log_tab, text="Logs")
        self.notebook.add(self.discord_tab, text="Discord Bot")
        self.notebook.add(self.config_tab, text="Default Config")
        self.notebook.add(self.network_tab, text="Network")  # Add network tab
        
        self.notebook.pack(expand=1, fill="both")
        
        self.config = configparser.ConfigParser()
        self.discord_bot = None
        self.compute_devices = []
        self.network_devices = []  # List to store network devices
        self.network_device_frames = {}

        self.default_cores = tk.IntVar(value=1)
        self.default_memory = tk.DoubleVar(value=1)
        self.default_cache_dir = tk.StringVar()
        
        self.setup_main_tab()
        self.setup_devices_tab()
        self.setup_log_tab()
        self.setup_discord_tab()
        self.setup_config_tab()
        self.setup_network_tab()
        self.check_and_download_client()
        
        self.detect_compute_devices()
        self.load_config()

        self.server_socket = None
        self.client_socket = None

    def setup_network_tab(self):
        self.network_mode = tk.StringVar(value="standalone")
        ttk.Radiobutton(self.network_tab, text="Standalone", variable=self.network_mode, value="standalone", command=self.update_network_mode).pack()
        ttk.Radiobutton(self.network_tab, text="Server", variable=self.network_mode, value="server", command=self.update_network_mode).pack()
        ttk.Radiobutton(self.network_tab, text="Client", variable=self.network_mode, value="client", command=self.update_network_mode).pack()

        self.server_frame = ttk.Frame(self.network_tab)
        ttk.Button(self.server_frame, text="Start Server", command=self.start_server).pack()
        self.server_status = ttk.Label(self.server_frame, text="Server: Not running")
        self.server_status.pack()

        self.client_frame = ttk.Frame(self.network_tab)
        ttk.Label(self.client_frame, text="Server IP:").pack(side=tk.LEFT)
        self.server_ip = ttk.Entry(self.client_frame)
        self.server_ip.pack(side=tk.LEFT)
        ttk.Button(self.client_frame, text="Connect", command=self.connect_to_server).pack(side=tk.LEFT)
        self.client_status = ttk.Label(self.client_frame, text="Client: Not connected")
        self.client_status.pack()

        self.network_devices_frame = ttk.LabelFrame(self.network_tab, text="Network Devices")
        self.network_devices_frame.pack(fill=tk.BOTH, expand=True)

        # Create a canvas for scrolling
        self.network_canvas = tk.Canvas(self.network_devices_frame)
        self.network_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add a scrollbar to the canvas
        self.network_scrollbar = ttk.Scrollbar(self.network_devices_frame, orient=tk.VERTICAL, command=self.network_canvas.yview)
        self.network_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure the canvas
        self.network_canvas.configure(yscrollcommand=self.network_scrollbar.set)
        self.network_canvas.bind('<Configure>', lambda e: self.network_canvas.configure(scrollregion=self.network_canvas.bbox("all")))

        # Create another frame inside the canvas
        self.network_inner_frame = ttk.Frame(self.network_canvas)

        # Add that frame to a window in the canvas
        self.network_canvas.create_window((0, 0), window=self.network_inner_frame, anchor="nw")

    def update_network_mode(self):
        mode = self.network_mode.get()
        if mode == "server":
            self.server_frame.pack()
            self.client_frame.pack_forget()
        elif mode == "client":
            self.server_frame.pack_forget()
            self.client_frame.pack()
        else:
            self.server_frame.pack_forget()
            self.client_frame.pack_forget()

    def start_server(self):
        if not self.server_socket:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind(('0.0.0.0', 36745))
            self.server_socket.listen(5)
            threading.Thread(target=self.accept_clients, daemon=True).start()
            self.server_status.config(text="Server: Running")

    def accept_clients(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()

    def handle_client(self, client_socket, addr):
        client_id = f"{addr[0]}:{addr[1]}"
        self.network_devices.append((client_socket, addr))
        self.create_network_device_frame(client_id)
        
        while True:
            try:
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                message = json.loads(data)
                self.handle_client_message(message, client_id)
            except:
                break
        
        self.remove_network_device_frame(client_id)
        self.network_devices = [(s, a) for s, a in self.network_devices if a != addr]
        client_socket.close()

    def create_network_device_frame(self, client_id):
        frame = ttk.LabelFrame(self.network_inner_frame, text=client_id)
        frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(frame, text="Start", command=lambda: self.send_to_client(client_id, {"action": "start_all"})).pack(side=tk.LEFT)
        ttk.Button(frame, text="Pause", command=lambda: self.send_to_client(client_id, {"action": "pause_all"})).pack(side=tk.LEFT)
        ttk.Button(frame, text="Resume", command=lambda: self.send_to_client(client_id, {"action": "resume_all"})).pack(side=tk.LEFT)
        ttk.Button(frame, text="Stop", command=lambda: self.send_to_client(client_id, {"action": "stop_all"})).pack(side=tk.LEFT)
        ttk.Button(frame, text="Quit", command=lambda: self.send_to_client(client_id, {"action": "quit_all"})).pack(side=tk.LEFT)

        status_label = ttk.Label(frame, text="Status: Connected")
        status_label.pack(side=tk.LEFT)

        self.network_device_frames[client_id] = {"frame": frame, "status_label": status_label}
        self.network_canvas.configure(scrollregion=self.network_canvas.bbox("all"))

    def remove_network_device_frame(self, client_id):
        if client_id in self.network_device_frames:
            self.network_device_frames[client_id]["frame"].destroy()
            del self.network_device_frames[client_id]
            self.network_canvas.configure(scrollregion=self.network_canvas.bbox("all"))

    def update_network_devices_list(self):
        self.network_devices_listbox.delete(0, tk.END)
        for _, addr in self.network_devices:
            self.network_devices_listbox.insert(tk.END, f"{addr[0]}:{addr[1]}")

    def connect_to_server(self):
        if not self.client_socket:
            try:
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.connect((self.server_ip.get(), 36745))
                self.client_status.config(text="Client: Connected")
                threading.Thread(target=self.receive_from_server, daemon=True).start()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to connect: {str(e)}")

    def receive_from_server(self):
        while True:
            try:
                data = self.client_socket.recv(1024).decode()
                if not data:
                    break
                message = json.loads(data)
                self.handle_server_message(message)
            except:
                break
        self.client_socket.close()
        self.client_socket = None
        self.client_status.config(text="Client: Not connected")

    def handle_server_message(self, message):
        if "action" in message:
            if message["action"] == "start_all":
                self.start_all_clients()
            elif message["action"] == "pause_all":
                self.send_command_all("pause")
            elif message["action"] == "resume_all":
                self.send_command_all("resume")
            elif message["action"] == "stop_all":
                self.send_command_all("stop")
            elif message["action"] == "quit_all":
                self.send_command_all("quit")

    def handle_client_message(self, message, client_id):
        if "status" in message:
            if client_id in self.network_device_frames:
                self.network_device_frames[client_id]["status_label"].config(text=f"Status: {message['status']}")

    def send_to_server(self, message):
        if self.client_socket:
            self.client_socket.send(json.dumps(message).encode())
    
    def send_to_client(self, client_id, message):
        for socket, addr in self.network_devices:
            if f"{addr[0]}:{addr[1]}" == client_id:
                socket.send(json.dumps(message).encode())
                break

    def setup_main_tab(self):
        ttk.Button(self.main_tab, text="Start All Clients", command=self.start_all_clients).pack()
        ttk.Button(self.main_tab, text="Pause All Clients", command=lambda: self.send_command_all("pause")).pack()
        ttk.Button(self.main_tab, text="Resume All Clients", command=lambda: self.send_command_all("resume")).pack()
        ttk.Button(self.main_tab, text="Exit After Current Frame (All)", command=lambda: self.send_command_all("stop")).pack()
        ttk.Button(self.main_tab, text="Exit Now (All)", command=lambda: self.send_command_all("quit")).pack()
        ttk.Button(self.main_tab, text="Kill All Clients", command=self.kill_all_clients).pack()
        ttk.Button(self.main_tab, text="Quit All Clients After Current Frames And Close Manager", command=self.quit_after_frames).pack()
        ttk.Button(self.main_tab, text="Quit All Clients Now And Close Manager", command=self.quit_now).pack()

        self.stats_frame = ttk.LabelFrame(self.main_tab, text="Stats")
        self.stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.update_stats()
    
    def setup_devices_tab(self):
        # Create a canvas
        self.devices_canvas = tk.Canvas(self.devices_tab)
        self.devices_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add a scrollbar to the canvas
        self.devices_scrollbar = ttk.Scrollbar(self.devices_tab, orient=tk.VERTICAL, command=self.devices_canvas.yview)
        self.devices_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure the canvas
        self.devices_canvas.configure(yscrollcommand=self.devices_scrollbar.set)
        self.devices_canvas.bind('<Configure>', lambda e: self.devices_canvas.configure(scrollregion=self.devices_canvas.bbox("all")))

        # Create another frame inside the canvas
        self.devices_frame = ttk.Frame(self.devices_canvas)

        # Add that frame to a window in the canvas
        self.devices_canvas.create_window((0, 0), window=self.devices_frame, anchor="nw")

        # Bind mousewheel to the canvas
        self.devices_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        self.devices_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def update_scrollregion(self):
        self.devices_canvas.configure(scrollregion=self.devices_canvas.bbox("all"))
    
    def setup_log_tab(self):
        self.log_notebook = ttk.Notebook(self.log_tab)
        self.log_notebook.pack(fill=tk.BOTH, expand=True)

    def save_bot_config(self):
        self.save_config()
        messagebox.showinfo("Config Saved", "Bot configuration has been saved.")

    def stop_bot(self):
        if messagebox.askyesno("Stop Bot", "Are you sure you want to stop the Discord bot?"):
            if self.discord_bot:
                asyncio.run_coroutine_threadsafe(self.discord_bot.close(), self.discord_bot.loop)
                self.discord_bot = None
                self.log("Discord bot stopped")
            else:
                self.log("Discord bot is not running")

    def setup_discord_tab(self):
        ttk.Label(self.discord_tab, text="Bot Token:").pack()
        self.bot_token = tk.StringVar()
        ttk.Entry(self.discord_tab, textvariable=self.bot_token, show="*").pack()

        ttk.Label(self.discord_tab, text="User ID (for DMs):").pack()
        self.user_id = tk.StringVar()
        ttk.Entry(self.discord_tab, textvariable=self.user_id).pack()

        self.use_dm = tk.BooleanVar()
        ttk.Checkbutton(self.discord_tab, text="Use DMs", variable=self.use_dm).pack()

        self.start_bot_on_startup = tk.BooleanVar()
        ttk.Checkbutton(self.discord_tab, text="Start bot when manager starts up", variable=self.start_bot_on_startup).pack()

        self.notify_crash = tk.BooleanVar()
        ttk.Checkbutton(self.discord_tab, text="Notify if client crashed", variable=self.notify_crash).pack()

        self.notify_restart = tk.BooleanVar()
        ttk.Checkbutton(self.discord_tab, text="Notify if client restarted", variable=self.notify_restart).pack()

        self.notify_quit = tk.BooleanVar()
        ttk.Checkbutton(self.discord_tab, text="Notify if client quits", variable=self.notify_quit).pack()

        self.send_logs_quit = tk.BooleanVar()
        ttk.Checkbutton(self.discord_tab, text="Send logs in txt file after client quits", variable=self.send_logs_quit).pack()

        self.send_logs_crash = tk.BooleanVar()
        ttk.Checkbutton(self.discord_tab, text="Send logs in txt file if client crashes", variable=self.send_logs_crash).pack()

        ttk.Button(self.discord_tab, text="Start Discord Bot", command=self.start_discord_bot).pack()
        ttk.Button(self.discord_tab, text="Save Bot Config", command=self.save_bot_config).pack()
        ttk.Button(self.discord_tab, text="Stop Bot", command=self.stop_bot).pack()

    def setup_config_tab(self):
        self.default_login = tk.StringVar()
        self.default_password = tk.StringVar()
        self.default_auto_restart = tk.BooleanVar(value=True)
        self.default_start_on_startup = tk.BooleanVar(value=False)
        self.default_verbose = tk.BooleanVar(value=False)
        self.default_headless = tk.BooleanVar(value=False)
        self.default_max_frame_time = tk.IntVar(value=0)
        self.default_sandbox = tk.BooleanVar(value=False)
        self.default_disable_large_downloads = tk.BooleanVar(value=False)
        self.default_custom_args = tk.StringVar()
        
        ttk.Label(self.config_tab, text="Default Login:").pack()
        ttk.Entry(self.config_tab, textvariable=self.default_login).pack()
        
        ttk.Label(self.config_tab, text="Default Password (Render Key recommended):").pack()
        ttk.Entry(self.config_tab, textvariable=self.default_password, show="*").pack()
        
        ttk.Checkbutton(self.config_tab, text="Auto-restart", variable=self.default_auto_restart).pack()
        ttk.Checkbutton(self.config_tab, text="Start SheepIt on manager start", variable=self.default_start_on_startup).pack()
        ttk.Checkbutton(self.config_tab, text="Verbose", variable=self.default_verbose).pack()
        ttk.Checkbutton(self.config_tab, text="Headless (Block Eevee)", variable=self.default_headless).pack()
        
        ttk.Label(self.config_tab, text="Max frame time (minutes):").pack()
        ttk.Entry(self.config_tab, textvariable=self.default_max_frame_time).pack()
        
        ttk.Checkbutton(self.config_tab, text="Run on sandbox", variable=self.default_sandbox).pack()
        ttk.Checkbutton(self.config_tab, text="Disable large downloads", variable=self.default_disable_large_downloads).pack()
        
        ttk.Label(self.config_tab, text="Default Custom Args:").pack()
        ttk.Entry(self.config_tab, textvariable=self.default_custom_args).pack()
        
        ttk.Button(self.config_tab, text="Export Config", command=self.export_config).pack()
        ttk.Button(self.config_tab, text="Import Config", command=self.import_config).pack()
        ttk.Button(self.config_tab, text="Save Config", command=self.save_config).pack()
        ttk.Label(self.config_tab, text="Default Threads:").pack()
        ttk.Entry(self.config_tab, textvariable=self.default_cores).pack()
        ttk.Label(self.config_tab, text="Default Memory:").pack()
        ttk.Entry(self.config_tab, textvariable=self.default_memory).pack()
        
        ttk.Label(self.config_tab, text="Default Cache Directory:").pack()
        cache_frame = ttk.Frame(self.config_tab)
        cache_frame.pack(fill=tk.X)
        ttk.Entry(cache_frame, textvariable=self.default_cache_dir).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(cache_frame, text="📁", command=self.select_default_cache_dir).pack(side=tk.RIGHT)

    def select_default_cache_dir(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.default_cache_dir.set(folder_selected)

    def detect_compute_devices(self):
        # Detect CPU
        cpu_threads = psutil.cpu_count(logical=True)
        cpu_device = ComputeDevice(f"CPU ({cpu_threads} threads)", "CPU")
        self.compute_devices.append(cpu_device)

        # Detect GPUs
        try:
            gpu_info = subprocess.check_output(["java", "-jar", "client.jar", "--show-gpu"], universal_newlines=True)
            gpu_matches = re.findall(r"GPU_ID\s+:\s+(\w+)\nLong ID\s+:\s+(.+)\nModel\s+:\s+(.+)\nMemory, MB:\s+(\d+)", gpu_info)
            
            for gpu_id, long_id, model, memory in gpu_matches:
                if "NVIDIA" in long_id:
                    gpu_device = ComputeDevice(f"GPU - {model}", gpu_id)
                    self.compute_devices.append(gpu_device)
                else:
                    print(f"WARNING: {model} is not supported by SheepIt")
        except:
            self.log("Failed to detect GPUs")

        self.create_device_widgets()

    def create_device_widgets(self):
        for i, device in enumerate(self.compute_devices):
            device.frame = ttk.LabelFrame(self.devices_frame, text=device.name)
            device.frame.pack(fill=tk.X, padx=5, pady=5)

            ttk.Checkbutton(device.frame, text="Enable", variable=device.enabled).grid(row=0, column=0)
            
            ttk.Checkbutton(device.frame, text="Use Default Values", variable=device.using_default, command=lambda d=device: self.toggle_default_values(d)).grid(row=0, column=1)
            ttk.Label(device.frame, text="Login:").grid(row=1, column=0)
            ttk.Entry(device.frame, textvariable=device.login).grid(row=1, column=1)
            
            ttk.Label(device.frame, text="Password:").grid(row=2, column=0)
            ttk.Entry(device.frame, textvariable=device.password, show="*").grid(row=2, column=1)
            
            ttk.Label(device.frame, text="Threads:").grid(row=3, column=0)
            ttk.Spinbox(device.frame, from_=2, to=psutil.cpu_count(logical=True), textvariable=device.cores).grid(row=3, column=1)
            
            ttk.Label(device.frame, text="Memory (GB):").grid(row=4, column=0)
            ttk.Spinbox(device.frame, from_=0.1, to=psutil.virtual_memory().total // (1024**3), increment=0.1, textvariable=device.memory).grid(row=4, column=1)
            
            ttk.Label(device.frame, text="Custom Args:").grid(row=5, column=0)
            ttk.Entry(device.frame, textvariable=device.custom_args).grid(row=5, column=1)

            cache_frame = ttk.Frame(device.frame)
            cache_frame.grid(row=6, column=0, columnspan=2, sticky="ew")
            ttk.Label(cache_frame, text="Cache Directory:").pack(side=tk.LEFT)
            ttk.Entry(cache_frame, textvariable=device.cache_dir).pack(side=tk.LEFT, expand=True, fill=tk.X)
            ttk.Button(cache_frame, text="📁", command=lambda d=device: self.select_cache_dir(d)).pack(side=tk.RIGHT)

            ttk.Label(device.frame, text="Proxy:").grid(row=7, column=0)
            ttk.Entry(device.frame, textvariable=device.proxy).grid(row=7, column=1)

            ttk.Label(device.frame, text="Max Rendertime (min):").grid(row=8, column=0)
            ttk.Spinbox(device.frame, from_=0, to=1440, textvariable=device.max_rendertime).grid(row=8, column=1)

            ttk.Checkbutton(device.frame, text="Auto-restart", variable=device.auto_restart).grid(row=9, column=0)
            ttk.Checkbutton(device.frame, text="Start on manager start", variable=device.start_on_manager_start).grid(row=9, column=1)
            ttk.Checkbutton(device.frame, text="Verbose", variable=device.verbose).grid(row=10, column=0)
            ttk.Checkbutton(device.frame, text="Headless (Block Eevee)", variable=device.headless).grid(row=10, column=1)
            ttk.Checkbutton(device.frame, text="Run on sandbox", variable=device.sandbox).grid(row=11, column=0)
            ttk.Checkbutton(device.frame, text="Disable large downloads", variable=device.disable_large_downloads).grid(row=11, column=1)

            ttk.Button(device.frame, text="Start", command=lambda d=device: self.start_client(d)).grid(row=12, column=0)
            ttk.Button(device.frame, text="Pause", command=lambda d=device: self.send_command(d, "pause")).grid(row=12, column=1)
            ttk.Button(device.frame, text="Resume", command=lambda d=device: self.send_command(d, "resume")).grid(row=13, column=0)
            ttk.Button(device.frame, text="Exit after frame", command=lambda d=device: self.send_command(d, "stop")).grid(row=13, column=1)
            ttk.Button(device.frame, text="Exit now", command=lambda d=device: self.send_command(d, "quit")).grid(row=14, column=0)
            ttk.Button(device.frame, text="Kill Client", command=lambda d=device: self.kill_client(d)).grid(row=14, column=1)
            
            ttk.Label(device.frame, text="Client Name (No spaces):").grid(row=15, column=0)
            ttk.Entry(device.frame, textvariable=device.client_name).grid(row=15, column=1)

            ttk.Label(device.frame, text="Priority:").grid(row=16, column=0)
            ttk.Spinbox(device.frame, from_=-19, to=19, textvariable=device.priority).grid(row=16, column=1)

            device.status_label = ttk.Label(device.frame, text="Status: OFF")
            device.status_label.grid(row=17, column=0, columnspan=2)

            ttk.Button(device.frame, text="Save Config", command=lambda d=device: self.save_device_config(d)).grid(row=18, column=0, columnspan=2)

            device.command_display = tk.Text(device.frame, height=3, wrap=tk.WORD)
            device.command_display.grid(row=19, column=0, columnspan=2, sticky="ew")
            device.command_display.config(state=tk.DISABLED)

            # Create log tab for this device
            log_frame = ttk.Frame(self.log_notebook)
            device.log_text = scrolledtext.ScrolledText(log_frame, state='disabled')
            device.log_text.pack(expand=True, fill='both')
            self.log_notebook.add(log_frame, text=device.name)

            ttk.Button(log_frame, text="Export Log", command=lambda d=device: self.export_log(d)).pack()
            

    def toggle_default_values(self, device):
        if device.using_default.get():
            self.apply_default_values(device)
        else:
            self.restore_custom_values(device)
        self.update_command_displays()

    def apply_default_values(self, device):
        device.login.set(self.default_login.get())
        device.password.set(self.default_password.get())
        device.cores.set(self.default_cores.get())
        device.memory.set(self.default_memory.get())
        device.custom_args.set(self.default_custom_args.get())
        device.auto_restart.set(self.default_auto_restart.get())
        device.verbose.set(self.default_verbose.get())
        device.headless.set(self.default_headless.get())
        device.sandbox.set(self.default_sandbox.get())
        device.disable_large_downloads.set(self.default_disable_large_downloads.get())
        device.start_on_manager_start.set(self.default_start_on_startup.get())
        device.cache_dir.set(self.default_cache_dir.get())
        device.max_rendertime.set(self.default_max_frame_time.get())

    def restore_custom_values(self, device):
        device.login.set(device.login.get())
        device.password.set(device.password.get())
        device.cores.set(device.cores.get())
        device.memory.set(device.memory.get())
        device.custom_args.set(device.custom_args.get())
        device.auto_restart.set(device.auto_restart.get())
        device.verbose.set(device.verbose.get())
        device.headless.set(device.headless.get())
        device.sandbox.set(device.sandbox.get())
        device.disable_large_downloads.set(device.disable_large_downloads.get())
        device.cache_dir.set(device.cache_dir.get())
        device.max_rendertime.set(device.max_rendertime.get())
        device.start_on_manager_start.set(device.start_on_manager_start.get())
        

    def save_device_config(self, device):
        self.save_config() 
        self.log(f"Configuration saved for {device.name}")

    def update_stats(self):
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        row = 0
        for device in self.compute_devices:
            ttk.Label(self.stats_frame, text=f"{device.name}:").grid(row=row, column=0, sticky="w")
            ttk.Label(self.stats_frame, text=f"Current Job: {device.current_job}").grid(row=row, column=1, sticky="w")
            ttk.Button(self.stats_frame, text="Block project", command=lambda d=device: self.send_command(d, "block")).grid(row=row, column=2)
            ttk.Label(self.stats_frame, text=f"Progress: {device.progress}%").grid(row=row+1, column=1, sticky="w")
            ttk.Label(self.stats_frame, text=f"Points: {device.points_generated}").grid(row=row+2, column=1, sticky="w")
            ttk.Label(self.stats_frame, text=f"Time: {device.time_running}").grid(row=row+3, column=1, sticky="w")
            ttk.Label(self.stats_frame, text=f"Status: {device.status}").grid(row=row+4, column=1, sticky="w")
            ttk.Label(self.stats_frame, text=f"User: {device.login.get()}").grid(row=row+5, column=1, sticky="w")
            row += 6

        ttk.Label(self.stats_frame, text="All Stats:").grid(row=row, column=0, sticky="w")
        total_time = sum((d.time_running for d in self.compute_devices), start=timedelta())
        total_points = sum(d.points_generated for d in self.compute_devices)
        total_dl = sum(d.downloads for d in self.compute_devices)
        total_up = sum(d.uploads for d in self.compute_devices)
        ttk.Label(self.stats_frame, text=f"Total Time: {total_time}").grid(row=row+1, column=1, sticky="w")
        ttk.Label(self.stats_frame, text=f"Total Points: {total_points}").grid(row=row+2, column=1, sticky="w")
        ttk.Label(self.stats_frame, text=f"Total DL/UP: {total_dl:.2f}GB / {total_up:.2f}GB").grid(row=row+3, column=1, sticky="w")

        self.master.after(5000, self.update_stats)  # Update every 5 seconds

    def start_client(self, device):
        if not os.path.exists("client.jar"):
            self.download_client()

        with device.status_lock:
            if device.process:
                self.log(f"Client for {device.name} is already running")
                return
        
        command = ["java", "-jar", "client.jar",
                "-login", device.login.get(),
                "-password", device.password.get(),
                "-ui", "text",
                "-cores", str(device.cores.get()),
                "-memory", f"{device.memory.get():.1f}G"]
        
        if device.gpu_id != "CPU":
            command.extend(["-gpu", device.gpu_id])

        if self.client_socket:
            self.send_to_server(f"Starting client for {device.name}")
        
        if device.verbose.get():
            command.append("--verbose")
        
        if device.headless.get():
            command.append("--headless")
        
        if device.sandbox.get():
            command.append("-server")
            command.append("https://sandbox.sheepit-renderfarm.com")
        
        if device.disable_large_downloads.get():
            command.append("--disable-large-downloads")
        
        if device.cache_dir.get():
            command.extend(["-cache-dir", device.cache_dir.get()])
        
        if device.proxy.get():
            command.extend(["-proxy", device.proxy.get()])
        
        if device.max_rendertime.get() > 0:
            command.extend(["-rendertime", str(device.max_rendertime.get())])
        
        custom_args = device.custom_args.get().split()
        command.extend(custom_args)

        if device.client_name.get():
            command.extend(["-hostname", device.client_name.get()])
        
        if device.priority.get() is not None:
            command.extend(["-priority", str(device.priority.get())])
        
        device.command_display.config(state=tk.NORMAL)
        device.command_display.delete('1.0', tk.END)
        device.command_display.insert(tk.END, " ".join(command))
        device.command_display.config(state=tk.DISABLED)

        if not device.cache_dir.get():
            base_dir = self.default_cache_dir.get()
            if base_dir:
                device_index = self.compute_devices.index(device)
                device_dir = f"{base_dir}{device_index}"
                device.cache_dir.set(device_dir)
                command.extend(["-cache-dir", device_dir])

        try:
            device.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, universal_newlines=True)
            device.start_time = datetime.now()
            threading.Thread(target=self.read_output, args=(device,), daemon=True).start()
            self.log(f"SheepIt client started for {device.name}")
            with device.status_lock:
                device.status = "RUNNING"
                device.status_label.config(text=f"Status: {device.status}")
        except Exception as e:
            self.log(f"Failed to start SheepIt client for {device.name}: {str(e)}")


    def stop_client(self, device):
        if self.client_socket:
            self.send_to_server(f"Stopping client for {device.name}")
        if device.process:
            device.process.terminate()
            device.process = None
            self.log(f"SheepIt client stopped for {device.name}")
            device.status = "OFF"
            device.status_label.config(text=f"Status: {device.status}")
        else:
            self.log(f"No client is running for {device.name}")

    def send_command(self, device, command):
        if device.process:
            try:
                device.process.stdin.write(f"{command}\n")
                device.process.stdin.flush()
                self.log(f"Sent command '{command}' to {device.name}")
                with device.status_lock:
                    if command == "pause":
                        device.status = "PAUSED"
                    elif command == "resume":
                        device.status = "RUNNING"
                    elif command in ["stop", "quit"]:
                        device.status = "CLOSING"
                        device.closing = True
                    device.status_label.config(text=f"Status: {device.status}")
            except Exception as e:
                self.log(f"Failed to send command to {device.name}: {str(e)}")
        else:
            self.log(f"No client is running for {device.name}")

    def read_output(self, device):
        while device.process:
            try:
                line = device.process.stdout.readline()
                if not line:
                    break
                self.parse_log(device, line.strip())
                self.log(line.strip(), device)  # Pass the device here
            except Exception as e:
                self.log(f"Error reading output from {device.name}: {str(e)}", device)  # And here
                break
        
        with device.status_lock:
            if device.closing:
                device.status = "OFF"
                device.closing = False
            elif device.status != "OFF":
                device.status = "CRASHED"
                if self.notify_crash.get():
                    self.send_discord_notification(f"{device.name} has crashed!")
                if self.send_logs_crash.get():
                    self.export_log(device, send_to_discord=True)
            else:
                if self.notify_quit.get():
                    self.send_discord_notification(f"{device.name} has quit")
                if self.send_logs_quit.get():
                    self.export_log(device, send_to_discord=True)
        
            device.status_label.config(text=f"Status: {device.status}")
            device.process = None

        if device.status == "CRASHED" and device.auto_restart.get():
            self.log(f"Restarting client for {device.name}")
            if self.notify_restart.get():
                self.send_discord_notification(f"Restarting {device.name}")
            self.start_client(device)

    def parse_log(self, device, line):
        def convert_to_gb(value, unit):
            # Convert the given value to MB based on the unit
            unit = unit.upper()
            if unit == "MB":
                return value / 1024  # 1 GB = 1024 MB
            elif unit == "GB":
                return value  # Already in GB
            elif unit == "TB":
                return value * 1024  # 1 TB = 1024 GB
            return value
        if "Rendering project" in line:
            device.current_job = line.split('"')[1]
        elif "Rendering" in line and "%" in line:
            try:
                device.progress = int(line.split("%")[0].split()[-1])
            except ValueError:
                pass
        elif "Credits earned:" in line:
            try:
                match = re.search(r"Credits earned:\s*(\d+)", line)
                if match:
                    device.points_generated = int(match.group(1))  
            except ValueError:
                pass
        
        elif "Session downloads:" in line:
            try:
                # Regex to match the download/upload values and their units (MB, GB, TB)
                match = re.search(r"Session downloads:\s*([\d.]+)([MGT]B).*Uploads:\s*([\d.]+)([MGT]B)", line)
                if match:
                    download_value = float(match.group(1))
                    download_unit = match.group(2)
                    upload_value = float(match.group(3))
                    upload_unit = match.group(4)

                    # Convert both downloads and uploads to MB
                    device.downloads = convert_to_gb(download_value, download_unit)
                    device.uploads = convert_to_gb(upload_value, upload_unit)
            except (ValueError, IndexError):
                pass
            
        try:
            device.time_running = datetime.now() - device.start_time
        except AttributeError:
            device.time_running = timedelta()

    def log(self, message, device=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        if device:
            if device.log_text:
                device.log_text.configure(state='normal')
                device.log_text.insert(tk.END, formatted_message + "\n")
                device.log_text.configure(state='disabled')
                device.log_text.see(tk.END)
        else:
            for d in self.compute_devices:
                if d.log_text:
                    d.log_text.configure(state='normal')
                    d.log_text.insert(tk.END, formatted_message + "\n")
                    d.log_text.configure(state='disabled')
                    d.log_text.see(tk.END)

    def export_log(self, device, send_to_discord=False):
        if send_to_discord:
            log_content = device.log_text.get("1.0", tk.END)
            self.send_discord_file(f"{device.name}_log.txt", log_content)
        else:
            file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                     filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
            if file_path:
                with open(file_path, "w") as file:
                    file.write(device.log_text.get("1.0", tk.END))
                self.log(f"Log exported for {device.name}")

    def start_all_clients(self):
        for device in self.compute_devices:
            if device.enabled.get():
                self.start_client(device)
        if self.client_socket:
            self.send_to_server({"status": "Started all clients"})

    def send_command_all(self, command):
        for device in self.compute_devices:
            if device.status != "OFF":
                self.send_command(device, command)

    def kill_client(self, device):
        if messagebox.askyesno("Kill Client", "Are you sure you want to kill this client? This may hang frames!"):
            with device.status_lock:
                if device.process:
                    device.process.kill()
                    device.process = None
                    self.log(f"Client for {device.name} has been forcibly terminated")
                    device.status = "OFF"
                    device.status_label.config(text=f"Status: {device.status}")

    def kill_all_clients(self):
        if messagebox.askyesno("Kill All Clients", "Are you sure you want to kill all clients? This may hang frames!"):
            for device in self.compute_devices:
                self.kill_client(device)

    def quit_after_frames(self):
        if messagebox.askyesno("Quit After Frames", "Are you sure you want to quit all clients after current frames and close the manager?"):
            self.send_command_all("stop")  # Command to stop clients
            self.check_clients_status() 

    def quit_now(self):
        if messagebox.askyesno("Quit Now", "Are you sure you want to quit all clients now and close the manager?"):
            self.send_command_all("quit")
            self.check_clients_status()

    def check_clients_status(self):
        all_off = all(device.status == "OFF" for device in self.compute_devices)  # Check if all devices are OFF
        if all_off:
            self.master.quit()  # Quit when all clients have stopped
        else:
            self.master.after(1000, self.check_clients_status)

    def start_discord_bot(self):
        token = self.bot_token.get()
        if not token:
            messagebox.showerror("Error", "Please enter a Discord bot token.")
            return

        intents = discord.Intents.default()
        intents.message_content = True
        self.discord_bot = commands.Bot(command_prefix='!', intents=intents)

        @self.discord_bot.event
        async def on_ready():
            self.log(f'Logged in as {self.discord_bot.user}')
            if self.use_dm.get() and self.user_id.get():
                user = await self.discord_bot.fetch_user(int(self.user_id.get()))
                await user.send("Bot is now online!")

        @self.discord_bot.command()
        async def status(ctx):
            status_message = "SheepIt clients status:\n"
            for device in self.compute_devices:
                status_message += f"{device.name}: {device.status}\n"
            await ctx.send(status_message)

        threading.Thread(target=self.discord_bot.run, args=(token,), daemon=True).start()
        self.log("Discord bot started")

    def send_discord_notification(self, message):
        if self.discord_bot and self.discord_bot.is_ready():
            asyncio.run_coroutine_threadsafe(self.send_discord_message(message), self.discord_bot.loop)

    async def send_discord_message(self, message):
        if self.use_dm.get() and self.user_id.get():
            user = await self.discord_bot.fetch_user(int(self.user_id.get()))
            await user.send(message)
        else:
            for guild in self.discord_bot.guilds:
                for channel in guild.text_channels:
                    await channel.send(message)
                    return

    def send_discord_file(self, filename, content):
        if self.discord_bot and self.discord_bot.is_ready():
            asyncio.run_coroutine_threadsafe(self.send_discord_file_async(filename, content), self.discord_bot.loop)

    async def send_discord_file_async(self, filename, content):
        with open(filename, "w") as f:
            f.write(content)
        if self.use_dm.get() and self.user_id.get():
            user = await self.discord_bot.fetch_user(int(self.user_id.get()))
            await user.send(file=discord.File(filename))
        else:
            for guild in self.discord_bot.guilds:
                for channel in guild.text_channels:
                    await channel.send(file=discord.File(filename))
                    break
                break
        os.remove(filename)

    def save_config(self):
        config = {
            "default_login": self.default_login.get(),
            "default_password": self.default_password.get(),
            "default_auto_restart": self.default_auto_restart.get(),
            "default_start_on_startup": self.default_start_on_startup.get(),
            "default_verbose": self.default_verbose.get(),
            "default_headless": self.default_headless.get(),
            "default_max_frame_time": self.default_max_frame_time.get(),
            "default_sandbox": self.default_sandbox.get(),
            "default_disable_large_downloads": self.default_disable_large_downloads.get(),
            "default_cores": self.default_cores.get(),
            "default_memory": self.default_memory.get(),
            "default_cache_dir": self.default_cache_dir.get(),
            "default_custom_args": self.default_custom_args.get(),
            "discord_bot_token": self.bot_token.get(),
            "discord_user_id": self.user_id.get(),
            "discord_use_dm": self.use_dm.get(),
            "discord_start_on_startup": self.start_bot_on_startup.get(),
            "discord_notify_crash": self.notify_crash.get(),
            "discord_notify_restart": self.notify_restart.get(),
            "discord_notify_quit": self.notify_quit.get(),
            "discord_send_logs_quit": self.send_logs_quit.get(),
            "discord_send_logs_crash": self.send_logs_crash.get(),
            "devices": [{
                "name": device.name,
                "gpu_id": device.gpu_id,
                "enabled": device.enabled.get(),
                "login": device.login.get(),
                "password": device.password.get(),
                "cores": device.cores.get(),
                "memory": device.memory.get(),
                "custom_args": device.custom_args.get(),
                "auto_restart": device.auto_restart.get(),
                "verbose": device.verbose.get(),
                "headless": device.headless.get(),
                "sandbox": device.sandbox.get(),
                "disable_large_downloads": device.disable_large_downloads.get(),
                "start_on_manager_start": device.start_on_manager_start.get(),
                "cache_dir": device.cache_dir.get(),
                "proxy": device.proxy.get(),
                "max_rendertime": device.max_rendertime.get(),
                "client_name": device.client_name.get(),  # New field
                "priority": device.priority.get(),  # New field
            "using_default": device.using_default.get()
            } for device in self.compute_devices]
        }
        
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
        
        self.log("Configuration saved")

    def load_config(self):
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                
                self.apply_config(config)
                
                self.log("Configuration loaded")
                self.update_command_displays()
                
                if self.start_bot_on_startup.get():
                    self.start_discord_bot()
                
                for device in self.compute_devices:
                    if device.start_on_manager_start.get():
                        self.start_client(device)
            except json.JSONDecodeError:
                self.log("Error: Invalid JSON in config file")
            except Exception as e:
                self.log(f"Error loading config: {str(e)}")
        else:
            self.log("No config file found. Using default settings.")

    def select_cache_dir(self, device):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            base_dir = self.default_cache_dir.get() or folder_selected
            device_index = self.compute_devices.index(device)
            device_dir = os.path.join(base_dir, f"{device_index + 1}")
            
            device.cache_dir.set(device_dir)
        
    def export_config(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if file_path:
            with open(file_path, "w") as f:
                json.dump(self.get_current_config(), f, indent=4)
            self.log("Configuration exported")

    def import_config(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if file_path:
            with open(file_path, "r") as f:
                config = json.load(f)
            self.apply_config(config)
            self.log("Configuration imported")

    def get_current_config(self):
        return {
            "default_login": self.default_login.get(),
            "default_password": self.default_password.get(),
            "default_auto_restart": self.default_auto_restart.get(),
            "default_start_on_startup": self.default_start_on_startup.get(),
            "default_verbose": self.default_verbose.get(),
            "default_headless": self.default_headless.get(),
            "default_max_frame_time": self.default_max_frame_time.get(),
            "default_sandbox": self.default_sandbox.get(),
            "default_disable_large_downloads": self.default_disable_large_downloads.get(),
            "default_custom_args": self.default_custom_args.get(),
            "default_cores": self.default_cores.get(),
            "default_memory": self.default_memory.get(),
            "default_cache_dir": self.default_cache_dir.get(),
            "discord_bot_token": self.bot_token.get(),
            "discord_user_id": self.user_id.get(),
            "discord_use_dm": self.use_dm.get(),
            "discord_start_on_startup": self.start_bot_on_startup.get(),
            "discord_notify_crash": self.notify_crash.get(),
            "discord_notify_restart": self.notify_restart.get(),
            "discord_notify_quit": self.notify_quit.get(),
            "discord_send_logs_quit": self.send_logs_quit.get(),
            "discord_send_logs_crash": self.send_logs_crash.get(),
            "devices": [{
                "name": device.name,
                "gpu_id": device.gpu_id,
                "enabled": device.enabled.get(),
                "login": device.login.get(),
                "password": device.password.get(),
                "cores": device.cores.get(),
                "memory": device.memory.get(),
                "custom_args": device.custom_args.get(),
                "auto_restart": device.auto_restart.get(),
                "verbose": device.verbose.get(),
                "headless": device.headless.get(),
                "sandbox": device.sandbox.get(),
                "disable_large_downloads": device.disable_large_downloads.get(),
                "start_on_manager_start": device.start_on_manager_start.get(),
                "cache_dir": device.cache_dir.get(),
                "proxy": device.proxy.get(),
                "max_rendertime": device.max_rendertime.get(),
                "client_name": device.client_name.get(),
                "priority": device.priority.get(),
            } for device in self.compute_devices]
        }

    def apply_config(self, config):
        self.default_login.set(config.get("default_login", ""))
        self.default_password.set(config.get("default_password", ""))
        self.default_auto_restart.set(config.get("default_auto_restart", True))
        self.default_start_on_startup.set(config.get("default_start_on_startup", False))
        self.default_verbose.set(config.get("default_verbose", False))
        self.default_headless.set(config.get("default_headless", False))
        self.default_max_frame_time.set(config.get("default_max_frame_time", 0))
        self.default_sandbox.set(config.get("default_sandbox", False))
        self.default_disable_large_downloads.set(config.get("default_disable_large_downloads", False))
        self.default_custom_args.set(config.get("default_custom_args", ""))
        self.default_cores.set(config.get("default_cores", 1))
        self.default_memory.set(config.get("default_memory", 1))
        self.default_cache_dir.set(config.get("default_cache_dir", ""))
        
        self.bot_token.set(config.get("discord_bot_token", ""))
        self.user_id.set(config.get("discord_user_id", ""))
        self.use_dm.set(config.get("discord_use_dm", False))
        self.start_bot_on_startup.set(config.get("discord_start_on_startup", False))
        self.notify_crash.set(config.get("discord_notify_crash", False))
        self.notify_restart.set(config.get("discord_notify_restart", False))
        self.notify_quit.set(config.get("discord_notify_quit", False))
        self.send_logs_quit.set(config.get("discord_send_logs_quit", False))
        self.send_logs_crash.set(config.get("discord_send_logs_crash", False))
        
        for device_config in config.get("devices", []):
            matched_device = next((device for device in self.compute_devices 
                                if device.name == device_config["name"] and device.gpu_id == device_config["gpu_id"]), None)
            if matched_device:
                matched_device.using_default.set(device_config.get("using_default", True))
                if matched_device.using_default.get():
                    self.apply_default_values(matched_device)
                else:
                    matched_device.enabled.set(device_config.get("enabled", False))
                    matched_device.login.set(device_config.get("login", ""))
                    matched_device.password.set(device_config.get("password", ""))
                    matched_device.cores.set(device_config.get("cores", 1))
                    matched_device.memory.set(device_config.get("memory", 1))
                    matched_device.custom_args.set(device_config.get("custom_args", ""))
                    matched_device.auto_restart.set(device_config.get("auto_restart", True))
                    matched_device.verbose.set(device_config.get("verbose", False))
                    matched_device.headless.set(device_config.get("headless", False))
                    matched_device.sandbox.set(device_config.get("sandbox", False))
                    matched_device.disable_large_downloads.set(device_config.get("disable_large_downloads", False))
                    matched_device.start_on_manager_start.set(device_config.get("start_on_manager_start", False))
                    matched_device.cache_dir.set(device_config.get("cache_dir", ""))
                    matched_device.proxy.set(device_config.get("proxy", ""))
                    matched_device.max_rendertime.set(device_config.get("max_rendertime", 0))
                    matched_device.client_name.set(device_config.get("client_name", ""))  # New field
                    matched_device.priority.set(device_config.get("priority", 0))

        self.update_command_displays()


    def update_command_displays(self):
        for device in self.compute_devices:
            command = self.generate_command(device)
            device.command_display.config(state=tk.NORMAL)
            device.command_display.delete('1.0', tk.END)
            device.command_display.insert(tk.END, " ".join(command))
            device.command_display.config(state=tk.DISABLED)

    def generate_command(self, device):
        command = ["java", "-jar", "client.jar",
                "-login", device.login.get(),
                "-password", device.password.get(),
                "-ui", "text",
                "-cores", str(int(device.cores.get())),
                "-memory", f"{device.memory.get():.1f}G"]
        
        if device.gpu_id != "CPU":
            command.extend(["-gpu", device.gpu_id])
        
        if device.verbose.get():
            command.append("--verbose")
        
        if device.headless.get():
            command.append("--headless")
        
        if device.sandbox.get():
            command.append("-server")
            command.append("https://sandbox.sheepit-renderfarm.com")
        
        if device.disable_large_downloads.get():
            command.append("--disable-large-downloads")
        
        if device.cache_dir.get():
            command.extend(["-cache-dir", device.cache_dir.get()])
        
        if device.proxy.get():
            command.extend(["-proxy", device.proxy.get()])
        
        if device.max_rendertime.get() > 0:
            command.extend(["-max-rendertime", str(device.max_rendertime.get())])
        
        custom_args = device.custom_args.get().split()
        command.extend(custom_args)

        # Add client name and priority
        if device.client_name.get():
            command.extend(["-hostname", device.client_name.get()])
        
        if device.priority.get() is not None:
            command.extend(["-priority", str(device.priority.get())])
        
        return command

    
    def check_and_download_client(self):
        if not os.path.exists("client.jar"):
            self.download_client()

    def download_client(self):
        url = "https://www.sheepit-renderfarm.com/media/applet/client-latest.php"
        self.log("Downloading client.jar...")
        try:
            response = requests.get(url)
            with open("client.jar", "wb") as f:
                f.write(response.content)
            self.log("client.jar downloaded successfully")
        except Exception as e:
            self.log(f"Failed to download client.jar: {str(e)}")
            messagebox.showerror("Error", f"Failed to download client.jar: {str(e)}")

def main():
    root = tk.Tk()
    app = RenderFarmBot(root)
    root.mainloop()

if __name__ == "__main__":
    main()

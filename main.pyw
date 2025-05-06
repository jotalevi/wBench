import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import os
import platform
import time
import re
import random
import string
import ctypes
import sys
import shutil
import csv
from datetime import datetime

def is_admin():
    if platform.system() == "Windows":
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    else:
        return True

if not is_admin():
    if platform.system() == "Windows":
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

class HDDTester(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("wBench")
        self.geometry("400x700")

        if platform.system() == "Windows":
            self.attributes('-toolwindow', True)

        self.iconphoto(False, tk.PhotoImage(file="icon.png"))
        self.resizable(False, False)

        self.selected_drive = tk.StringVar()
        self.format_before_test = tk.BooleanVar()
        self.is_testing = False
        self.drives = {}

        self.create_widgets()
        self.refresh_drives()
        self.after(1000, self.auto_refresh_drives)

    def create_widgets(self):
        logo = tk.Label(self, text="wBench", font=("Consolas", 32, "bold"), anchor="center")
        logo.pack(pady=20)

        self.drive_menu = ttk.Combobox(self, textvariable=self.selected_drive, state="readonly", width=30)
        self.drive_menu.pack(pady=5)

        action_frame = tk.Frame(self)
        action_frame.pack(pady=10)

        self.format_checkbox = ttk.Checkbutton(action_frame, text="Format before testing", variable=self.format_before_test)
        self.format_checkbox.pack(side=tk.LEFT, padx=5)

        self.start_button = ttk.Button(action_frame, text="Start Benchmark", command=self.start_test)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.result_text = tk.Text(self, height=25, width=45)
        self.result_text.pack(fill="both", expand=True, padx=0, pady=0)

        self.status_label = tk.Label(self, text="Status: Waiting...", anchor="w")
        self.status_label.pack(fill="x", padx=0)

        style = ttk.Style()
        style.configure("Custom.Horizontal.TProgressbar", thickness=10)

        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate", style="Custom.Horizontal.TProgressbar")
        self.progress.pack(fill="x", padx=0, pady=(0, 0))

    def auto_refresh_drives(self):
        if not self.is_testing:
            self.refresh_drives()
        self.after(1000, self.auto_refresh_drives)

    def refresh_drives(self):
        self.drives.clear()
        drives_list = []

        if platform.system() == "Windows":
            result = subprocess.check_output("wmic logicaldisk get caption", shell=True).decode(errors='ignore').splitlines()
            for line in result:
                if ":" in line:
                    path = line.strip()
                    if path[0] != "C":
                        drives_list.append(path)
                        self.drives[path] = {"volume": path}
        else:
            disks = subprocess.check_output(["lsblk", "-dn", "-o", "NAME"]).decode().strip().splitlines()
            for name in disks:
                disk = f"/dev/{name}"
                drives_list.append(disk)
                self.drives[disk] = {"volume": disk}

        self.drive_menu['values'] = drives_list
        if not self.drive_menu.get():
            self.drive_menu.set("Select a disk")

    def start_test(self):
        if not self.selected_drive.get() or self.selected_drive.get() == "Select a disk":
            messagebox.showerror("Error", "Please select a drive first.")
            return

        if self.is_testing:
            messagebox.showinfo("Info", "A test is already running.")
            return

        self.is_testing = True
        self.progress['value'] = 0
        self.status_label.config(text="Status: Starting...")
        self.result_text.delete(1.0, tk.END)

        threading.Thread(target=self.run_tests).start()

    def run_tests(self):
        selected = self.drives[self.selected_drive.get()]
        volume = selected["volume"]
        results = {}

        try:
            self.update_progress(5, "Getting drive information...")
            info = self.get_drive_info(volume)
            results.update(info)

            if self.format_before_test.get():
                self.update_progress(10, "Formatting drive...")
                self.format_drive(volume)

            self.update_progress(20, "Testing Sequential Read...")
            read_speed = self.test_read_speed(volume)
            results['Sequential Read'] = f"{read_speed:.2f} MB/s" if read_speed else "Test Failed"

            self.update_progress(50, "Testing Sequential Write...")
            write_speed = self.test_write_speed(volume)
            results['Sequential Write'] = f"{write_speed:.2f} MB/s" if write_speed else "Test Failed"

            self.update_progress(75, "Testing Random IOPS...")
            random_iops = self.test_random_iops(volume)
            results['Random IOPS'] = f"{random_iops} IOPS" if random_iops else "Test Failed"

            self.update_progress(90, "Calculating Final Score...")
            score = self.calculate_score(read_speed, write_speed, random_iops)
            results['Final Score'] = f"{score:.2f}" if score > 0 else "Test Incomplete"

            results['Performance Rating'] = self.rate_performance(score)
            results['Health Status'] = "Healthy"

            self.update_progress(100, "Benchmark Complete!")
            self.display_results(results)
            self.export_results(results)

        except Exception as e:
            messagebox.showerror("Error", str(e))

        self.is_testing = False

    def get_drive_info(self, volume):
        info = {}
        try:
            if platform.system() == "Windows":
                ps_cmd = f"powershell Get-PhysicalDisk | Select-Object -Property FriendlyName, SerialNumber, Size | Format-List"
                result = subprocess.check_output(ps_cmd, shell=True).decode(errors='ignore')
                info['Drive Info'] = result.strip()
                match = re.search(r"FriendlyName\s+:\s+(.+)", result)
                serial = re.search(r"SerialNumber\s+:\s+(.+)", result)
                size = re.search(r"Size\s+:\s+(\d+)", result)
                info['Drive Model'] = match.group(1).strip() if match else "Unknown"
                info['Serial Number'] = serial.group(1).strip() if serial else "Unknown"
                info['Total Capacity'] = size.group(1).strip() + " bytes" if size else "Unknown"
            else:
                output = subprocess.check_output(["lsblk", "-o", "MODEL,SERIAL,SIZE", "-dn", volume]).decode()
                parts = output.strip().split()
                info['Drive Model'] = parts[0] if len(parts) >= 1 else "Unknown"
                info['Serial Number'] = parts[1] if len(parts) >= 2 else "Unknown"
                info['Total Capacity'] = parts[2] if len(parts) >= 3 else "Unknown"
        except Exception as e:
            info['Drive Info Error'] = str(e)
        return info

    def format_drive(self, volume):
        try:
            if platform.system() == "Windows":
                subprocess.run(["format", volume, "/FS:NTFS", "/Q", "/Y"], shell=True, check=True)
            else:
                subprocess.run(["sudo", "mkfs.ext4", volume], check=True)
        except Exception as e:
            raise Exception(f"Failed to format drive: {e}")

    def test_read_speed(self, volume):
        test_file = os.path.join(volume, "testfile.tmp") if platform.system() == "Windows" else "/tmp/testfile"
        size = 512 * 1024 * 1024  # 512MB

        if not os.path.exists(test_file):
            with open(test_file, "wb") as f:
                f.write(b"\0" * size)

        start = time.time()
        with open(test_file, "rb") as f:
            while f.read(1024 * 1024):
                pass
        end = time.time()

        if platform.system() == "Windows":
            os.remove(test_file)

        return round(size / (end - start) / (1024 * 1024), 2)

    def test_write_speed(self, volume):
        test_file = os.path.join(volume, "testfile.tmp") if platform.system() == "Windows" else "/tmp/testfile"
        size = 512 * 1024 * 1024  # 512MB
        start = time.time()
        with open(test_file, "wb") as f:
            f.write(b"\0" * size)
        end = time.time()

        if platform.system() == "Windows":
            os.remove(test_file)

        return round(size / (end - start) / (1024 * 1024), 2)

    def test_random_iops(self, volume):
        test_file = os.path.join(volume, "testfile.tmp") if platform.system() == "Windows" else "/tmp/testfile"
        size = 128 * 1024 * 1024
        if not os.path.exists(test_file):
            with open(test_file, "wb") as f:
                f.write(b"\0" * size)

        block_size = 4096
        blocks = size // block_size
        reads = 1000
        start = time.time()
        with open(test_file, "rb") as f:
            for _ in range(reads):
                f.seek(random.randint(0, blocks - 1) * block_size)
                f.read(block_size)
        end = time.time()

        if platform.system() == "Windows":
            os.remove(test_file)

        return int(reads / (end - start))

    def calculate_score(self, read, write, iops):
        if read > 0 and write > 0 and iops > 0:
            return (read + write + (iops / 10)) / 3
        else:
            return 0

    def rate_performance(self, score):
        if score >= 200:
            return "Excellent"
        elif score >= 100:
            return "Good"
        elif score >= 50:
            return "OK"
        elif score > 0:
            return "Poor"
        return "N/A"

    def update_progress(self, value, status):
        self.progress['value'] = value
        self.status_label.config(text=f"Status: {status}")
        self.update()

    def display_results(self, results):
        self.result_text.insert(tk.END, "Benchmark and Drive Information:\n")
        for k, v in results.items():
            self.result_text.insert(tk.END, f"{k}: {v}\n")
        self.result_text.insert(tk.END, "\n✅ Benchmark Complete and Saved to CSV.\n")

    def export_results(self, results):
        os.makedirs("benchmark_results", exist_ok=True)
        filename = f"benchmark_results/benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(filename, "w", newline='') as csvfile:
            writer = csv.writer(csvfile)
            for k, v in results.items():
                writer.writerow([k, v])

if __name__ == "__main__":
    app = HDDTester()
    app.mainloop()

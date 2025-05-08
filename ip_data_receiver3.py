# -*- coding: utf-8 -*-

import socket
import json
import tkinter as tk
from tkinter import messagebox
import threading
import time
import pandas as pd
import re

# 스레드 종료를 위한 이벤트
stop_event = threading.Event()
file_lock = threading.Lock()  # 파일 접근 보호를 위한 Lock

def convert_txt_to_excel(input_txt='thermal_camera_data.txt', output_excel='thermal_data_by_area.xlsx'):
    try:
        with open(input_txt, "r", encoding="utf-8") as f:
            raw_data = f.read()

        json_blocks = re.findall(r'\[\s*{.*?}\s*\]', raw_data, re.DOTALL)
        sheets = {}

        for block in json_blocks:
            try:
                data_list = json.loads(block)
                for entry in data_list:
                    area_id = entry.pop("area_id")
                    if area_id not in sheets:
                        sheets[area_id] = []
                    sheets[area_id].append(entry)
            except Exception as e:
                print(f"[ERROR] Failed to parse JSON block: {e}")

        with pd.ExcelWriter(output_excel, engine="xlsxwriter") as writer:
            for area_id, records in sheets.items():
                df = pd.DataFrame(records)
                df.index += 1
                df.to_excel(writer, sheet_name=f"area_{area_id}", index_label="Index")

        print(f"[LOG] Excel file saved: {output_excel}")
    except Exception as e:
        print(f"[ERROR] Failed to convert txt to Excel: {e}")

def receive_data(host, port, output_file='thermal_camera_data.txt'):
    print(f"[LOG] Attempting to connect to {host}:{port}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            s.connect((host, port))
            print(f"[LOG] Successfully connected to {host}:{port}")

            while not stop_event.is_set():
                try:
                    print("[LOG] Waiting to receive data...")
                    data = s.recv(4096)
                    if not data:
                        break

                    try:
                        data = data.decode('utf-8')
                    except UnicodeDecodeError as e:
                        print(f"[LOG] Decoding error: {e}. Skipping data.")
                        continue

                    with file_lock:
                        with open(output_file, 'a') as file:
                            try:
                                parsed_data = json.loads(data)
                                file.write(json.dumps(parsed_data, indent=4))
                            except json.JSONDecodeError:
                                file.write(data)
                            file.write('\n')

                    print(f"[LOG] Data received and saved to {output_file}")

                    # 엑셀 자동 변환
                    convert_txt_to_excel(output_file)

                    time.sleep(1)

                except Exception as e:
                    print(f"[ERROR] Error receiving data: {e}")
                    messagebox.showerror("Data Error", f"An error occurred while receiving data: {e}")
                    break
    except socket.timeout:
        print(f"[ERROR] Connection to {host}:{port} timed out.")
        messagebox.showerror("Connection Timeout", f"Connection to {host}:{port} timed out.")
    except Exception as e:
        print(f"[ERROR] Connection error: {e}")
        messagebox.showerror("Connection Error", f"An error occurred: {e}")
    finally:
        print("[LOG] Receive loop terminated.")

def start_receiving():
    global stop_event
    stop_event.clear()
    host = ip_entry.get()
    port = int(port_entry.get())
    output_file = output_entry.get() if output_entry.get() else "thermal_camera_data.txt"

    try:
        print("[LOG] Starting receiving thread...")
        receive_thread = threading.Thread(target=receive_data, args=(host, port, output_file))
        receive_thread.daemon = True
        receive_thread.start()
        print("[LOG] Receiving thread started.")
    except Exception as e:
        print(f"[ERROR] Failed to start thread: {e}")
        messagebox.showerror("Thread Error", f"Failed to start receiving thread: {e}")

def stop_receiving():
    stop_event.set()
    print("[LOG] Stop event set. Waiting for threads to terminate...")
    messagebox.showinfo("Stopped", "Data receiving stopped.")

# GUI 설정
app = tk.Tk()
app.title("Thermal Camera Data Receiver")
app.geometry("400x250")

tk.Label(app, text="IP Address:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
ip_entry = tk.Entry(app)
ip_entry.grid(row=0, column=1, padx=10, pady=10)
ip_entry.insert(0, "192.168.0.140")

tk.Label(app, text="Port:").grid(row=1, column=0, padx=10, pady=10, sticky="e")
port_entry = tk.Entry(app)
port_entry.grid(row=1, column=1, padx=10, pady=10)
port_entry.insert(0, "60110")

tk.Label(app, text="Output File:").grid(row=2, column=0, padx=10, pady=10, sticky="e")
output_entry = tk.Entry(app)
output_entry.grid(row=2, column=1, padx=10, pady=10)
output_entry.insert(0, "thermal_camera_data.txt")

receive_button = tk.Button(app, text="Start Receiving", command=start_receiving)
receive_button.grid(row=3, column=0, columnspan=2, pady=10)

stop_button = tk.Button(app, text="Stop Receiving", command=stop_receiving)
stop_button.grid(row=4, column=0, columnspan=2, pady=10)

def on_closing():
    stop_receiving()
    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing)
app.mainloop()
# -*- coding: utf-8 -*-

import socket
import json
import tkinter as tk
from tkinter import messagebox
import threading
import time
import pandas as pd
import re
import matplotlib.pyplot as plt
import os
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# 스레드 종료를 위한 이벤트
stop_event = threading.Event()
file_lock = threading.Lock()

data_store = {}  # area_id별 데이터 누적 저장용
plot_lock = threading.Lock()

# 그래프 설정
fig, ax = plt.subplots()
canvas = None
area_vars = {}
metric_vars = {
    'temp_max': tk.BooleanVar(value=True),
    'temp_min': tk.BooleanVar(value=True),
    'temp_avr': tk.BooleanVar(value=True)
}

def update_plot():
    with plot_lock:
        ax.clear()
        values = data_store.get(0, [])[-60:]  # 최대 60초치 데이터만 유지
        x = list(range(len(values)))

        if metric_vars['temp_max'].get():
            y_max = [v['temp_max'] for v in values]
            ax.plot(x, y_max, label='temp_max', color='red')

        if metric_vars['temp_min'].get():
            y_min = [v['temp_min'] for v in values]
            ax.plot(x, y_min, label='temp_min', color='blue')

        if metric_vars['temp_avr'].get():
            y_avr = [v['temp_avr'] for v in values]
            ax.plot(x, y_avr, label='temp_avr', color='green')

        ax.set_ylim(-20, 120)
        ax.set_title("Area 0 - Temperature Metrics")
        ax.set_ylabel("Temperature (°C)")
        ax.set_xlabel("Time (seconds)")
        ax.grid(True)
        ax.legend(loc='upper left')
        canvas.draw()

        # 최신 값 텍스트 업데이트
        if values:
            latest = values[-1]
            label_temp_max.config(text=f"최대: {latest['temp_max']}℃")
            label_temp_min.config(text=f"최소: {latest['temp_min']}℃")
            label_temp_avr.config(text=f"평균: {latest['temp_avr']}℃")

def convert_txt_to_excel(input_txt='thermal_camera_data.txt', output_excel='thermal_data_by_area.xlsx'):
    try:
        with open(input_txt, "r", encoding="utf-8") as f:
            raw_data = f.read()

        json_blocks = re.findall(r'\[\s*{.*?}\s*\]', raw_data, re.DOTALL)
        sheets = {}
        latest_data = {}  # area_id별 최신값 저장용

        for block in json_blocks:
            try:
                data_list = json.loads(block)
                for entry in data_list:
                    area_id = entry.pop("area_id")
                    if area_id not in sheets:
                        sheets[area_id] = []
                    sheets[area_id].append(entry)
                    latest_data[area_id] = entry  # 가장 마지막 값 저장
            except Exception as e:
                print(f"[ERROR] Failed to parse JSON block: {e}")

        with pd.ExcelWriter(output_excel, engine="xlsxwriter") as writer:
            for area_id, records in sheets.items():
                df = pd.DataFrame(records)
                df.index += 1
                df.to_excel(writer, sheet_name=f"area_{area_id}", index_label="Index")

        print(f"[LOG] Excel file saved: {output_excel}")
        return latest_data

    except Exception as e:
        print(f"[ERROR] Failed to convert txt to Excel: {e}")
        return {}

        cb.pack(anchor="w")

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

                    # 파일 저장
                    with file_lock:
                        with open(output_file, 'a') as file:
                            try:
                                fixed_data = data.strip()
                                if fixed_data.startswith('[') and not fixed_data.endswith(']'):
                                    fixed_data += ']'
                                parsed_data = json.loads(fixed_data)
                                file.write(json.dumps(parsed_data, indent=4))
                            except json.JSONDecodeError:
                                file.write(data)
                            file.write('\n')

                    # 실시간 파싱 → 시각화용 저장
                    try:
                        fixed_data = data.strip()
                        if fixed_data.startswith('[') and not fixed_data.endswith(']'):
                            fixed_data += ']'
                        parsed = json.loads(fixed_data)
                        for item in parsed:
                            area_id = item["area_id"]
                            if area_id not in data_store:
                                data_store[area_id] = []
                            data_store[area_id].append(item)
                            if area_id == 0 and len(data_store[area_id]) > 60:
                                data_store[area_id] = data_store[area_id][-60:]
                    except Exception as e:
                        print(f"[ERROR] Failed to parse real-time data: {e}")

                    app.after(0, update_plot)
                    convert_txt_to_excel(output_file)
                    time.sleep(1)

                except Exception as e:
                    print(f"[ERROR] Error receiving data: {e}")
                    show_error_message("Data Error", f"An error occurred while receiving data: {e}")
                    break

    except socket.timeout:
        print(f"[ERROR] Connection to {host}:{port} timed out.")
        show_error_message("Connection Timeout", f"Connection to {host}:{port} timed out.")
    except Exception as e:
        print(f"[ERROR] Connection error: {e}")
        show_error_message("Connection Error", f"An error occurred: {e}")
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
        show_error_message("Thread Error", f"Failed to start receiving thread: {e}")

def stop_receiving():
    stop_event.set()
    print("[LOG] Stop event set. Waiting for threads to terminate...")
    messagebox.showinfo("Stopped", "Data receiving stopped.")

# GUI 설정
app = tk.Tk()
app.title("Thermal Camera Data Receiver")
app.geometry("1000x600")

tk.Label(app, text="IP Address:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
ip_entry = tk.Entry(app)
ip_entry.grid(row=0, column=1, padx=10, pady=5)
ip_entry.insert(0, "192.168.0.140")

tk.Label(app, text="Port:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
port_entry = tk.Entry(app)
port_entry.grid(row=1, column=1, padx=10, pady=5)
port_entry.insert(0, "60110")

tk.Label(app, text="Output File:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
output_entry = tk.Entry(app)
output_entry.grid(row=2, column=1, padx=10, pady=5)
output_entry.insert(0, "thermal_camera_data.txt")

receive_button = tk.Button(app, text="Start Receiving", command=start_receiving)
receive_button.grid(row=3, column=0, columnspan=2, pady=10)

stop_button = tk.Button(app, text="Stop Receiving", command=stop_receiving)
stop_button.grid(row=4, column=0, columnspan=2, pady=10)


metric_frame = tk.LabelFrame(app, text="Metrics")
metric_frame.grid(row=0, column=3, rowspan=3, padx=10, pady=10, sticky="n")

for metric, var in metric_vars.items():
    cb = tk.Checkbutton(metric_frame, text=metric, variable=var, command=update_plot)
    cb.pack(anchor="w")

# 그래프 표시
fig.set_size_inches(6, 4)
canvas = FigureCanvasTkAgg(fig, master=app)
canvas.get_tk_widget().grid(row=6, column=0, columnspan=4, pady=10)

# 현재 온도 표시 라벨
temp_frame = tk.LabelFrame(app, text="현재 온도 (Area 0)", padx=10, pady=5)
temp_frame.grid(row=0, column=4, rowspan=3, padx=10, pady=10, sticky="n")

label_temp_max = tk.Label(temp_frame, text="최대: -")
label_temp_max.pack(anchor="w")

label_temp_min = tk.Label(temp_frame, text="최소: -")
label_temp_min.pack(anchor="w")

label_temp_avr = tk.Label(temp_frame, text="평균: -")
label_temp_avr.pack(anchor="w")

def show_error_message(title, message):
    app.after(0, lambda: messagebox.showerror(title, message))

def on_closing():
    stop_receiving()
    time.sleep(1.1)
    app.quit()
    app.destroy()
    os._exit(0)

app.protocol("WM_DELETE_WINDOW", on_closing)
app.mainloop()

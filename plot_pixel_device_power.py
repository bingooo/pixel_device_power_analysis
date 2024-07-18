import subprocess
import re
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime
import csv
import os
import pandas as pd
import atexit

# 正则表达式来解析日志数据
time_regex = re.compile(r"(\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})")
power_total_regex = re.compile(r"total power: ([\d.]+) mW for (\d+) ms")
power_rails_regex = re.compile(r"Power rails \[([\s\S]+)\]")

# CSV文件初始化
csv_file = 'stat.csv'
if not os.path.exists(csv_file):
    with open(csv_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Timestamp', 'Total Power (mW)'])

# 创建 pandas DataFrame
data = {
    'Timestamp': [],
    'TotalPower(mW)': []
}
df = pd.DataFrame(data)

# 解析单个日志行并更新 DataFrame
def parse_log_line(line):
    global df
    
    time_match = time_regex.search(line)
    if not time_match:
        return
    
    log_time_str = "2024-" + time_match.group(1)
    log_time = datetime.strptime(log_time_str, "%Y-%m-%d %H:%M:%S.%f")
    
    total_power_match = power_total_regex.search(line)
    if total_power_match:
        total_power_value = float(total_power_match.group(1))
        new_row = pd.DataFrame([[log_time, total_power_value]], columns=("Timestamp", "TotalPower(mW)"))
        df = pd.concat([df, new_row], ignore_index=True)

    power_rails_matches = power_rails_regex.findall(line)
    for match in power_rails_matches:
        rail_data = match.split('] [')
        for rail in rail_data:
            rail_name, rail_value = rail.split(': ')
            rail_value = float(rail_value.split(' ')[0])
            if rail_name not in df.columns:
                df[rail_name] = None  # 创建新的列，并初始化为 None
            df.loc[df['Timestamp'] == log_time, rail_name] = rail_value

# 实时更新图像
def animate(i):
    ax1.clear()
    ax1.plot(df['Timestamp'], df['TotalPower(mW)'], label='TotalPower(mW)')
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Total Power (mW)')
    ax1.legend(ncol=2, loc='upper left', fontsize='6')
    
    ax2.clear()
    for column in df.columns:
        if column != 'Timestamp' and column != 'TotalPower(mW)':
            ax2.plot(df['Timestamp'], df[column], label=f'{column} (mW)')
    ax2.set_xlabel('Time')
    ax2.set_ylabel('Power by Rail (mW)')
    ax2.legend(ncol=2, loc='upper left', fontsize='6')

# 设置图像
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

# 启动adb logcat
process = subprocess.Popen(['adb', 'logcat', '-s', 'pixel-thermal', '-T', '1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

# 实时读取日志数据并解析
def read_log():
    while True:
        line = process.stdout.readline()
        if not line:
            break
        if "Power rails" in line or "total power" in line:
            parse_log_line(line)

# 注册退出时的处理函数，将数据写入CSV文件
@atexit.register
def save_data_to_csv():
    df.to_csv(csv_file, index=False)

# 使用matplotlib的animation来实时更新图像
ani = animation.FuncAnimation(fig, animate, interval=1000)

# 启动读取日志的线程
import threading
log_thread = threading.Thread(target=read_log)
log_thread.start()

plt.show()

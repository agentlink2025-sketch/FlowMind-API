#!/usr/bin/env python3
"""
日志监控脚本
用于实时监控API日志，分析网络异常和性能问题
"""

import time
import re
from collections import defaultdict, Counter
from datetime import datetime, timedelta

def parse_log_line(line):
    """解析日志行"""
    # 日志格式: 2024-12-19 10:30:45,123 - __main__ - INFO - [req_1234567890] 消息内容
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d{3}) - (\w+) - (\w+) - (.*)'
    match = re.match(pattern, line)
    
    if match:
        timestamp_str, millis, logger_name, level, message = match.groups()
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        return {
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'logger': logger_name
        }
    return None

def extract_request_id(message):
    """提取请求ID"""
    match = re.search(r'\[(req_\d+|miniprogram_\d+|network_check_\d+)\]', message)
    return match.group(1) if match else None

def analyze_logs(log_file='api.log', last_minutes=10):
    """分析最近几分钟的日志"""
    print(f"🔍 分析最近 {last_minutes} 分钟的日志...")
    print("=" * 60)
    
    cutoff_time = datetime.now() - timedelta(minutes=last_minutes)
    
    # 统计信息
    stats = {
        'total_requests': 0,
        'successful_requests': 0,
        'failed_requests': 0,
        'timeout_errors': 0,
        'connection_errors': 0,
        'api_errors': 0,
        'retry_attempts': 0,
        'avg_response_time': 0,
        'request_times': [],
        'error_types': Counter(),
        'requests_by_id': defaultdict(list)
    }
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                log_entry = parse_log_line(line.strip())
                if not log_entry or log_entry['timestamp'] < cutoff_time:
                    continue
                
                message = log_entry['message']
                request_id = extract_request_id(message)
                
                if request_id:
                    stats['requests_by_id'][request_id].append(log_entry)
                
                # 统计请求类型
                if '收到miniprogram请求' in message:
                    stats['total_requests'] += 1
                elif '请求处理完成' in message:
                    stats['successful_requests'] += 1
                elif 'HTTP异常' in message or '未知异常' in message:
                    stats['failed_requests'] += 1
                elif '超时' in message:
                    stats['timeout_errors'] += 1
                elif '连接错误' in message:
                    stats['connection_errors'] += 1
                elif 'API返回错误' in message:
                    stats['api_errors'] += 1
                elif '重试' in message:
                    stats['retry_attempts'] += 1
                
                # 提取响应时间
                time_match = re.search(r'耗时: ([\d.]+)秒', message)
                if time_match:
                    response_time = float(time_match.group(1))
                    stats['request_times'].append(response_time)
                
                # 统计错误类型
                if 'ERROR' in log_entry['level']:
                    if '超时' in message:
                        stats['error_types']['超时'] += 1
                    elif '连接' in message:
                        stats['error_types']['连接错误'] += 1
                    elif 'API' in message:
                        stats['error_types']['API错误'] += 1
                    else:
                        stats['error_types']['其他错误'] += 1
    
    except FileNotFoundError:
        print(f"❌ 日志文件 {log_file} 不存在")
        return
    except Exception as e:
        print(f"❌ 读取日志文件时出错: {e}")
        return
    
    # 计算平均响应时间
    if stats['request_times']:
        stats['avg_response_time'] = sum(stats['request_times']) / len(stats['request_times'])
    
    # 打印统计结果
    print(f"📊 统计结果 (最近 {last_minutes} 分钟):")
    print(f"   总请求数: {stats['total_requests']}")
    print(f"   成功请求: {stats['successful_requests']}")
    print(f"   失败请求: {stats['failed_requests']}")
    print(f"   成功率: {(stats['successful_requests'] / max(stats['total_requests'], 1) * 100):.1f}%")
    print(f"   平均响应时间: {stats['avg_response_time']:.2f}秒")
    print(f"   重试次数: {stats['retry_attempts']}")
    print()
    
    print("🚨 错误统计:")
    for error_type, count in stats['error_types'].most_common():
        print(f"   {error_type}: {count}次")
    print()
    
    # 分析具体请求
    print("🔍 详细请求分析:")
    for request_id, entries in list(stats['requests_by_id'].items())[-5:]:  # 显示最近5个请求
        print(f"\n   请求 {request_id}:")
        for entry in entries:
            timestamp = entry['timestamp'].strftime('%H:%M:%S.%f')[:-3]
            level = entry['level']
            message = entry['message']
            print(f"     {timestamp} [{level}] {message}")

def monitor_realtime(log_file='api.log'):
    """实时监控日志"""
    print("🔍 开始实时监控日志...")
    print("按 Ctrl+C 停止监控")
    print("=" * 60)
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            # 移动到文件末尾
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if line:
                    log_entry = parse_log_line(line.strip())
                    if log_entry:
                        timestamp = log_entry['timestamp'].strftime('%H:%M:%S.%f')[:-3]
                        level = log_entry['level']
                        message = log_entry['message']
                        
                        # 根据日志级别选择颜色
                        if level == 'ERROR':
                            print(f"🔴 {timestamp} [{level}] {message}")
                        elif level == 'WARNING':
                            print(f"🟡 {timestamp} [{level}] {message}")
                        elif '重试' in message:
                            print(f"🔄 {timestamp} [{level}] {message}")
                        elif '成功' in message:
                            print(f"✅ {timestamp} [{level}] {message}")
                        else:
                            print(f"ℹ️  {timestamp} [{level}] {message}")
                else:
                    time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n👋 监控已停止")
    except FileNotFoundError:
        print(f"❌ 日志文件 {log_file} 不存在")
    except Exception as e:
        print(f"❌ 监控出错: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'realtime':
        monitor_realtime()
    else:
        analyze_logs()

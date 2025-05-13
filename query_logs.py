from models import Session, MonitoredProcess, ProcessActivityLog
from datetime import datetime, timedelta
from collections import defaultdict

def print_monitored_processes():
    session = Session()
    try:
        processes = session.query(MonitoredProcess)\
            .order_by(MonitoredProcess.last_seen.desc())\
            .all()

        print("\n=== Monitored Processes ===")
        for proc in processes:
            print(f"\nProcess: {proc.process_name} (PID: {proc.pid})")
            print(f"Last Seen: {proc.last_seen}")
            if proc.last_uptime_seconds:
                print(f"Last Uptime: {timedelta(seconds=int(proc.last_uptime_seconds))}")
            print("-" * 30)

    finally:
        session.close()

def print_recent_activity(hours=24):
    session = Session()
    try:
        since = datetime.now() - timedelta(hours=hours)
        logs = session.query(ProcessActivityLog)\
            .join(MonitoredProcess)\
            .filter(ProcessActivityLog.start_time >= since)\
            .order_by(ProcessActivityLog.start_time.desc())\
            .all()

        # Dictionary to store accumulated durations
        process_durations = defaultdict(lambda: {'total_duration': timedelta(0), 'sessions': 0})

        print(f"\n=== Activity Logs (Last {hours} hours) ===")
        for log in logs:
            print(f"\nProcess: {log.process.process_name} (PID: {log.process.pid})")
            print(f"Session Start: {log.start_time}")
            print(f"Last Activity: {log.last_activity_time}")
            print(f"Session End: {log.end_time or 'Still running'}")
            
            if log.end_time:
                # Calculate and display the actual duration
                duration = log.end_time - log.start_time
                print(f"Session Duration: {duration} (End - Start)")
                
                # Accumulate duration for this process
                process_key = f"{log.process.process_name} (PID: {log.process.pid})"
                process_durations[process_key]['total_duration'] += duration
                process_durations[process_key]['sessions'] += 1
            
            print("-" * 50)

        # Print accumulated durations
        print("\n=== Total Activity Duration per Process ===")
        for process, stats in process_durations.items():
            print(f"\n{process}")
            print(f"Total Duration: {stats['total_duration']}")
            print(f"Number of Sessions: {stats['sessions']}")
            if stats['sessions'] > 0:
                avg_duration = stats['total_duration'] / stats['sessions']
                print(f"Average Session Duration: {avg_duration}")
            print("-" * 40)

    finally:
        session.close()

if __name__ == "__main__":
    print_monitored_processes()
    print_recent_activity()

import json, time
import threading
import traceback
import glob, os
from pathlib import Path
import subprocess

def call_a_script(filename, output_path):
    try:
        subprocess.run(["python3", "event_display.py", filename, output_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")

# GET LAST LINE OF FILE
def get_last_log_entry(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
        last_log = lines[-1].strip()
    file.close()
    return last_log

# GET NEWEST FILE SIZE
def get_newest_file(dir_path, dst = False):
    # Convert to Path object for easier manipulation
    directory_path = Path(dir_path)
    # List all files in the directory
    if dst:
        files = [file for file in directory_path.iterdir() if file.is_file()]
    else:
        files = [file for file in directory_path.iterdir() if file.is_file() and 'RawData' in file.name]
    # Get the newest file
    newest_file = max(files, key=lambda file: file.stat().st_mtime)
    # Get the size of the newest file
    file_size = newest_file.stat().st_size
    return file_size, newest_file.name

# SAVE TO LOG ENTRY
def save_last_log_entry(rc_file_path, dispatcher_file_path, output_file_path, daq_files_directory, event_display_directory, output_event_display_path):
    last_log_entry = get_last_log_entry(rc_file_path)
    log = {}

    with open(dispatcher_file_path, 'r') as file:
        lines = file.readlines()
        log["DAQ_status"] = lines[-2].strip()
        try:
            log["DAQ_summary_log"] = lines[-2].split(":")[3].strip()
        except:
            log["DAQ_summary_log"] = "Processing..."

        for line in reversed(lines):  # Start from the end of the file
            if "Run number" in line:
                log["run_number"] = line.split(":")[1].strip()
                break  # Break the loop once subrun number is found
            elif "Subrun number" in line:
                log["subrun_number"] = line.split(":")[1].strip()
            elif "ET file" in line:
                if "pdstl" in line:
                    log["mode"] = "Pedestal"
                elif "linjc" in line:
                    log["mode"] = "Light Injection"
                elif "numi" in line:
                    log["mode"] = "Numi Beam"
    file.close()

    # Saving log message
    log["message"] = last_log_entry.lstrip()
    if "DEBUG" in last_log_entry:
        log["type"] = "DEBUG"
    elif "INFO" in last_log_entry:
        log["type"] = "INFO"
    elif "WARNING" in last_log_entry:
        log["type"] = "WARNING"
    elif "ERROR" in last_log_entry:
        log["type"] = "ERROR"

    # Get last DST file generated
    DST_size, DST_last_file = get_newest_file(event_display_directory, dst=True)

    # Run event display
    call_a_script(event_display_directory + '/' + DST_last_file, output_event_display_path)

    # Saving daq file size
    log["daq_file_size"], log["daq_file_name"] = get_newest_file(daq_files_directory)

    with open(output_file_path, 'w') as output_file:
        json.dump(log, output_file)
    output_file.close()

# MAIN FUNCTION
def main():
    # Use last version of log files!
    try:
        while True:
            rc_file_path = '/work/logs/runcontrol.log'
            dispatcher_file_path = '/work/logs/readout_dispatcher.log'
            #output_log_file_path = '/home/nfs/minerva/Mx2_monitoring/last_log_entry.txt'
            output_log_file_path = '/home/acd/acdcs/2x2/MINERvA_DQM_PlotTransfer/last_log_entry.txt'
            daq_files_directory = '/work/data/rawdata'
            event_display_directory = '/work/data/dst'
            output_event_display_path = '/home/acd/acdcs/2x2/MINERvA_DQM_PlotTransfer/nearline_plots/event.png'
            save_last_log_entry(rc_file_path, dispatcher_file_path, output_log_file_path, daq_files_directory, event_display_directory, output_event_display_path)
            # Sleep for 10 seconds
            time.sleep(10)
    except Exception as e:
            print('*** Caught exception: %s: %s' % (e.__class__, e))
            traceback.print_exc()
            main()

# EXECUTE CONTINUOUS LOG READER
if __name__ == "__main__":
    threading.Thread(target=main).start()

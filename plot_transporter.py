import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone, timedelta
import pytz
import time
from influxdb import InfluxDBClient
import threading
import json
import traceback
from PIL import Image, ImageFont, ImageDraw

# GET TIME FROM FILE
def get_modification_time(input_path):
    # Get the modification time of the input image file
    modification_time = os.path.getmtime(input_path)
    utc_time = datetime.utcfromtimestamp(modification_time)
    # Format the Chicago time
    chicago_timezone = pytz.timezone('America/Chicago')
    chicago_time = utc_time.replace(tzinfo=timezone.utc).astimezone(chicago_timezone)
    return chicago_time.strftime("%m-%d-%Y %H:%M:%S")

# ADD TIMESTAMP ON TOP OF DQM PLOT
def add_margin(pil_img, creation_time, top, right, bottom, left, color):
    width, height = pil_img.size
    new_width = width + right + left
    new_height = height + top + bottom
    result = Image.new(pil_img.mode, (new_width, new_height), color)
    result.paste(pil_img, (left, top))
    draw = ImageDraw.Draw(result)
    font = ImageFont.truetype("/home/acd/acdcs/2x2/MINERvA_DQM_PlotTransfer/Roboto-Medium.ttf", 80, encoding="unic")
    # Add timestamp to the image
    draw.text((10, 10), "Modified at: " + creation_time, font=font)
    result.resize((200,200), resample=Image.LANCZOS)
    return result

# ADD TIMESTAMP ON TOP OF THE PNG FILE
def add_timestamp_to_image(input_path, output_path):
    # Get creation time of the input image file
    creation_time = get_modification_time(input_path)
    # Load the image
    Im=Image.open(input_path)
    im_new = add_margin(Im, creation_time, 100, 0, 0, 0, (0, 0, 0))
    im_new.save(output_path)

# GET TEXT FROM ONLINE COMPONENT (NuMI)
import requests
from bs4 import BeautifulSoup
def get_numi_status():
    # Fetch the webpage content
    response = requests.get("https://dbweb9.fnal.gov:8443/ifbeam/bmon/numimon/Display")
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')
    component = soup.find(id="tsa9")
    return component.get_text()

# EXECUTE CONTINUOUS PLOT TRANSFERING
def main():

    # Iterate over each file in the directory
    #directory = "/home/nfs/minerva/Mx2_Monitoring/Mx2_Nearline/plots_png"
    directory = "/home/acd/acdcs/2x2/MINERvA_DQM_PlotTransfer/nearline_plots"

    # Log entry file
    #log_entry_file = "/home/nfs/minerva/Mx2_monitoring/LogReader/last_log_entry.txt"
    log_entry_file = "/home/acd/acdcs/2x2/MINERvA_DQM_PlotTransfer/last_log_entry.txt"

    # Source InfluxDB connection settings
    source_host = '192.168.197.46'
    source_port = 8086

    # Connect to the source InfluxDB instance
    source_client = InfluxDBClient(source_host, source_port, "mx2_logs")
    source_client.create_database("mx2_logs")
    source_client.switch_database("mx2_logs")

    try:
        while True:
            for filename in os.listdir(directory):
                if filename.endswith(".png"):
                    # Input and output paths for each file
                    input_path = os.path.join(directory, filename)
                    output_path = os.path.join("/data/grafana/Mx2/", os.path.basename(input_path))
                    
                    # Add timestamp to the image
                    add_timestamp_to_image(input_path, output_path)
            
            # Add timestamp to the image
            add_timestamp_to_image(input_path, output_path)

            # Read JSON line from file
            log_entry_file = "/home/acd/acdcs/2x2/MINERvA_DQM_PlotTransfer/last_log_entry.txt"
            with open(log_entry_file, 'r') as file:
                json_line = file.readline().strip()
            data = json.loads(json_line)

            # Extract elements
            subrun_number = data['subrun_number']
            run_number = data['run_number']
            message = data['message']
            message_type = data['type']
            daq_status = data['DAQ_status']
            mode = data['mode']
            DAQ_summary_log = data['DAQ_summary_log']
            daq_file_size = data['daq_file_size']
            daq_file_name = data['daq_file_name']
            numi_status = get_numi_status()

            # Define data point
            data_point = {
                "measurement": "logs",
                "time": datetime.utcnow().strftime('%Y%m%d %H:%M:%S'),
                "fields": {
                    "run_number": int(run_number),
                    "subrun_number": int(subrun_number),
                    "type": message_type,
                    "message": message,
                    "daq_status" : daq_status,
                    "daq_summary_log" : DAQ_summary_log,
                    "daq_file_size" : daq_file_size,
                    "daq_file_name" : daq_file_name,
                    "numi_status" : numi_status,
                    "mode" : mode
                }
            }

            # Write data point to InfluxDB
            source_client.write_points([data_point])

            # Sleep for 10 seconds
            time.sleep(10)

    except Exception as e:
        print('*** Caught exception: %s: %s' % (e.__class__, e))
        traceback.print_exc()
        main()

# EXECUTE CONTINUOUS LOG READER
if __name__ == "__main__":
    threading.Thread(target=main).start()
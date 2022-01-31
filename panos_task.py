import argparse, time, sys, datetime, json, subprocess
import http.client as hc

def user_response(library_name):
    response = input(f'The required library "{library_name}" library was not found. Do you want me to attempt to install it for you? (y/n): ')

    if response == 'y':
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', library_name])
        except:
            sys.exit('The command "pip3" was not found. Please install pip3 on your system first before proeeding.')
    elif response == 'n':
        sys.exit('Quitting without installing the required library.')
    else:
        print('You entered an invalid option, please type in "y" or "n".')
        user_response(library_name)

try:
    global netmiko
    import netmiko
except:
    user_response("netmiko")
    
try:
    global apscheduler
    from apscheduler.schedulers.background import BackgroundScheduler as Scheduler
except:
    user_response("apscheduler")


import panos_lib


current_date_time = datetime.datetime.now()
print(f'Current date & time: {current_date_time.strftime("%Y/%m/%d %H:%M:%S")}')

parser = argparse.ArgumentParser()
parser.add_argument("--config-file", help="JSON config file containing SET and OPERATIONAL commands you want to run against a list of PAN-OS devices.")
parser.add_argument("--time", help="Time you would like to execute the script, using the following syntax: HH:MM:SS")
parser.add_argument('--date', help='Date you would like to execute the script, using the following syntax: YYYY-MM-DD')
parser.add_argument('--username', help='Username to log into the PAN-OS Device.')
parser.add_argument('--password', help='Password to log into the PAN-OS Device.')

args = parser.parse_args()

def validate_args_input():
    def validate_date_format(date):
        try:
            datetime.datetime.strptime(date, '%Y/%m/%d')
        except:
            sys.exit("Invalid date entered. Format must be YYYY/MM/DD.")

    def validate_time_format(time):
        try:
            datetime.datetime.strptime(time, '%H:%M:%S')
        except:
            sys.exit("Invalid time entered. Format must be HOUR:MINUTE:SECOND.")
    
    def validate_file_exists(file):
        pass

    if not args.config_file or not args.time or not args.date or not args.username or not args.password:
        sys.exit('Mandatory script parameters not specified. You are required to specify --config-file, --time, --date, username and password parameters.')
    else:
        validate_date_format(args.date)
        validate_time_format(args.time)
        validate_file_exists(args.config_file)

    return True

def set_job_timer():
    target_daytime = datetime.datetime.strptime(f'{args.date} {args.time}', '%Y/%m/%d %H:%M:%S')
    if target_daytime < datetime.datetime.now():
        sys.exit('The date and time you entered occurs in the past. Please verify you entered the correct date and time.')

    print("Target execution date & time specified:", target_daytime)

    now = datetime.datetime.now()
    if target_daytime < datetime.datetime.now():
        target_daytime += datetime.timedelta(days=1)

    print(f"Sleeping for {target_daytime-now}")
    time.sleep((target_daytime-now).total_seconds())

def read_file(filename):
    try:
        with open(filename, 'rt') as file_object:
            file_contents = file_object.read()
        return file_contents
    except:
        print('The file specified does not exist.')

def convert_json_to_dict(file_contents):
    try:
        json_to_dict_data = json.loads(file_contents)
    except:
        sys.exit('The JSON in the config file is not valid JSON data.')
    return json_to_dict_data

def check_if_key_exists(key_type, file_contents):
    if key_type in file_contents:
        return True
    else:
        return False

def validate_key_structure(key_type, file_contents): # dict data should be list type and have more than 1 entry in it
    if isinstance(file_contents[key_type], list):
        if len(file_contents[key_type]) > 0:
            return True
    print(f'The section "{key_type}" in the config file does not meet requirements and will be ignored. It should be a list of data containing one or more items.')
    return False

def validate_config_file_and_print_contents(key_type, key_type_friendly_name, file_contents):
    if check_if_key_exists(key_type, file_contents):
        if validate_key_structure(key_type, file_contents):
            #print("\n", key_type_friendly_name)
            #for item in file_contents[key_type]:
            #    print(item)
            return True
    return False

def main():
    if validate_args_input():
        set_job_timer()

        file_contents = read_file(args.config_file)
        file_data = convert_json_to_dict(file_contents)

        operational_commands_validation_status = False
        set_commands_validation_status = False

        if validate_config_file_and_print_contents('panos_devices', 'PAN-OS Devices:', file_data):
            if validate_config_file_and_print_contents('operational_commands', 'Operational Commands:', file_data):
                operational_commands_validation_status = True
            if validate_config_file_and_print_contents('set_commands', 'Set Commands:', file_data):
                set_commands_validation_status = True

            if operational_commands_validation_status or set_commands_validation_status:
                for device in file_data['panos_devices']:
                    panos_connection = panos_lib.connect_and_validate_ready(device, username=args.username, password=args.password)

                    if operational_commands_validation_status:
                        panos_lib.panos_send_commands(panos_connection, 'operational', file_data['operational_commands'])

                    if set_commands_validation_status:
                        panos_lib.panos_send_commands(panos_connection, 'configure', file_data['set_commands'])
                        panos_lib.commit(panos_connection)
                
                    panos_connection.disconnect()

        print(f'Completed tasks at: {datetime.datetime.now()}')

if __name__ == '__main__':
    main()

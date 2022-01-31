import logging, sys

import netmiko

def load_third_party_libraries():
    try:
        global netmiko
        import netmiko
    except:
        response = ''
        def read_response():
            response = input('The required library "Netmiko" library was not found. Do you want me to attempt to install it for you? (y/n)')
        if response == 'y':
            pass
        if response == 'n':
            sys.exit('Quitting without installing the required library.')
        else:
            print('You entered an invalid option, please type in "y" or "n".')
            read_response()

load_third_party_libraries()

AUTOCOMMIT_MAX_RETRIES = 45
AUTOCOMMIT_RETRY_SLEEP_TIME_SEC = 5

def connect_and_validate_ready(ip, **kwargs):
    def panos_command_successful(panos_connection):
        """
        Checks if the CLI is ready, responsive and responds to a command being sent to it.
        """
        print("Checking to see if PAN-OS is ready.")
        output = panos_connection.send_command('show system info')
        if "sw-version" in output:
            return True
        else: 
            return False

    def ssh_to_ngfw(**kwargs):
        """
        Initiates the connection and authenticates to the NGFW.
        """
        kwargs['device_type'] = 'paloalto_panos'
        if not 'username' in kwargs:
            kwargs['username'] = 'admin'

        if not 'password' in kwargs:
            kwargs['password'] = 'password'

        print(f'Connecting to {ip}...')
        try:
            connect = netmiko.ConnectHandler(**kwargs)
            return connect
        except netmiko.ssh_exception.NetmikoTimeoutException:
            logging.error('PAN-OS not ready: Connection timed out.')
            return False
        except netmiko.ssh_exception.NetMikoAuthenticationException:
            logging.error('PAN-OS not ready: Authentication failed.')
            return False
        except ValueError:
            logging.error('PAN-OS not ready: Value Error, SSH keys have not been generated yet.')
            return False
        except OSError:
            logging.error('PAN-OS not ready: Socket closed.')
            return False
        except Exception as e:
            logging.error('Unknown error: ')
            logging.error(e)
            return False

    connected = False
    connected = ssh_to_ngfw(ip=ip, **kwargs)
    if connected:
        print('Connected and authenticated.')

    if panos_command_successful(panos_connection=connected):
        print('PAN-OS is ready.\n')
        return connected
    
    return False

def enter_config_mode(panos_connection):
    if not panos_connection.check_config_mode():
        panos_connection.config_mode()

def commit(panos_connection):
    print('Committing changes.')
    panos_connection.commit()

def panos_send_commands(panos_connection, command_type, commands):
    """
    Accepts a list of commands, or individual command as a string
    """
    #print('Sending command(s):')
    def send_commands(panos_connection, commands):
        print_commit_message = False
        if isinstance(commands, list):
            for command in commands:
                if command != "commit":
                    print("Sending command:", command)
                    print("Command output: ")
                    print(panos_connection.send_command(command))
                else:
                    print_commit_message = True
        elif isinstance(commands, str):
            if commands != "commit":
                print(commands)
                print(panos_connection.send_command(commands))
            else:
                print_commit_message = True
        if print_commit_message:
            print("Ignoring commit command, as commit is performed automatically after set commands are all sent.")
    
    if command_type == 'operational':
        send_commands(panos_connection, commands)
    elif command_type == 'configure':
        enter_config_mode(panos_connection)
        send_commands(panos_connection, commands)
        panos_connection.exit_config_mode()
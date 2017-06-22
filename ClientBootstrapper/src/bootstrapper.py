import os
import socket
import sys
import logging
import platform
import json
import requests
import tempfile
import zipfile
import time
from subprocess import call

# Configure logging asap.
log = logging.getLogger("bootstrapper")
hdlr = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
log.addHandler(hdlr)
hdlr.setLevel(logging.DEBUG)
log.setLevel(logging.DEBUG)

#DISCOVERY_ADDR = "192.168.56.2"
DISCOVERY_ADDR = "255.255.255.255"
DISCOVERY_PORT = 9000


class ProtocolException(Exception):
    pass


class MissingAgent(Exception):
    pass


def install_root_ca(sniffer_url):
    """
    This method will download and install a self-signed certificate into the ROOT-CA repo.
    For now, we only support windows.
    :param sniffer_url: 
    :return: True if the installation succeeded, False otherwise.
    """

    if sniffer_url is None:
        raise ValueError("SnifferUrl parameter cannot be null.")

    # Download the CA into a temporary folder
    r = requests.get(sniffer_url)
    if r.status_code != 200:
        logging.exception("The bootstrapper was unable to download the certificate file from %s. "
                          "No certificate will be installed." % sniffer_url)
        return False

    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.write(r.content)
    tmp.flush()
    cert_file_name = tmp.name
    tmp.close()

    if os.name == 'nt':
        # Time to perform the installation via the CertUtil
        cmd = ['certutil', '-f', '-p', '', '-importpfx', cert_file_name]
        retcode = call(cmd, shell=True)
    else:
        raise NotImplementedError("The current version of the bootstrapper only supports Windows 7")

    return retcode == 0

def upgrade_agent(agent_url, dest_dir):
    # Make sure dest dir exists and is empty
    if not os.path.isdir(dest_dir):
        os.makedirs(dest_dir)
    else:
        log.info("Directory %s already exists. Its content will be overwritten." % agent_url)

    log.info("Attempting to download agent from %s..." % agent_url)
    r = requests.get(agent_url)

    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(r.content)
        tmp.flush()

        # Relocate the FD pointer to the beginning of the file
        tmp.seek(0)

        # Unzip the file
        z = zipfile.ZipFile(tmp)
        z.extractall(path=dest_dir)


def run_agent(path, command, hc_ip, hc_port):
    log.info("Time to start the agent!")
    os.chdir(path)
    os.system("%s %s %d" % (command, hc_ip, hc_port))  # returns the exit status


def main(argv):

    if len(argv) < 2:
        raise Exception("Invalid arguments specified. Please specify the PATH where to store the agent and the start command for the agent.")

    dest_dir = argv[0]
    command = argv[1]

    log.info("Starting up...")

    counter = 0

    # Create the socket and immediately advertise our presence
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('', 0))
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # 5 seconds timeout
    s.settimeout(5.0)

    # Create the helo message

    packet = {
        "msg": "HELO",
        "platform": str(platform.system()),
        "release": str(platform.release()),
        "arch": str(platform.machine())
    }
    """
    packet = {
        "msg": "HELO",
        "platform": "Windows",
        "release": "7",
        "arch": "x86"
    }
    """

    # Encode it into a string
    data = json.dumps(packet)

    while True:
        try:
            log.info("Querying network...")
            # Send the message
            s.sendto(data, (DISCOVERY_ADDR,DISCOVERY_PORT))
            log.info("Sending \n%s\nto %s:%d" % (data, DISCOVERY_ADDR, DISCOVERY_PORT))

            # Wait for the response
            sniffer_data, sniffer_addr = s.recvfrom(1024)
            log.info("Received response from %s:%d\n%s" % (sniffer_addr[0],sniffer_addr[1],sniffer_data))

            msg = json.loads(sniffer_data)
            code = msg.get('msg')
            hc_addr = msg.get('hc_addr')
            hc_port = msg.get('hc_port')
            agent_url = msg.get('agent_url')
            cert_url = msg.get('cert_url')

            # Is this the correct response ?
            if code is None or code != 'HELO_YOU':
                raise ProtocolException("Invalid message code received from server. Expecting HELO_YOU, received %s instead." % code)

            # Check if we have everything: HC_ADDR, HC_PORT, AGENT_URL
            if hc_addr is None:
                raise ProtocolException("Received message is lacking HC_ADDRESS")

            if hc_port is None:
                raise ProtocolException("Received message is lacking HC_PORT")

            if agent_url is None:
                raise MissingAgent("Received message is lacking AGENT_URL. This mens that the current Agent OS is not supported by the sniffer.")

            # At this point we have everything. Let's first download the agent
            upgrade_agent(agent_url, dest_dir)

            # Now download the CA certificate and install it
            if cert_url is not None:
                if not install_root_ca(cert_url):
                    raise Exception("Unable to install certificate.")
            else:
                logging.warning("The sniffer did not provide any certificate URL to be downloaded. Skipping "
                                "certificate installation.")

            # Now start the agent
            run_agent(dest_dir, command, hc_addr, hc_port)

        except socket.timeout:
            log.info("No response from any sniffer at attempt %d. Retrying..." % counter)
            counter += 1

        except:
            log.exception("Unsuccessful bootstrap attempt %d" % counter)
            counter += 1
        finally:
            time.sleep(1)

if __name__ == '__main__':
    main(sys.argv[1:])

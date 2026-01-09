import socket
import re
from rtp import RTP
import base64

from fHDHR.exceptions import TunerError

class Direct_RTP_Stream():
    """
    A method to stream rtp/s.
    """

    def __init__(self, fhdhr, stream_args, tuner):
        self.fhdhr = fhdhr
        self.stream_args = stream_args
        self.tuner = tuner

        #we handle RTSP and RTP. For RTSP we need to do setup over TCP and then stream RTP over UDP.
        proto = self.stream_args["stream_info"]["url"].strip().split('://')[0]
        if proto == 'rtsp':
            try:
                self.fhdhr.logger.info("RSTP Attempting to create socket to listen on.")
                self.address = self.get_sock_address()
                if not self.address:
                    raise TunerError("806 - Tune Failed: Could Not Create Socket")
                self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.tcp_socket.bind((self.address, 0))
                self.tcp_socket_address = self.tcp_socket.getsockname()[0]
                self.tcp_socket_port = self.tcp_socket.getsockname()[1]
                self.fhdhr.logger.info("Created TCP socket at %s:%s." % (self.tcp_socket_address, self.tcp_socket_port))

                self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_socket.bind((self.address, 0))
                self.udp_socket_address = self.udp_socket.getsockname()[0]
                self.udp_socket_port = self.udp_socket.getsockname()[1]
                self.udp_socket.settimeout(5)
                self.fhdhr.logger.info("Created UDP socket at %s:%s." % (self.udp_socket_address, self.udp_socket_port))

                credentials = "%s:%s" % (self.stream_args["stream_info"]["username"], self.stream_args["stream_info"]["password"])
                credentials_bytes = credentials.encode("ascii")
                credentials_base64_bytes = base64.b64encode(credentials_bytes)
                credentials_base64_string = credentials_base64_bytes.decode("ascii")

                self.describe = "DESCRIBE %s RTSP/1.0\r\nCSeq: 2\r\nUser-Agent: python\r\nAccept: application/sdp\r\nAuthorization: Basic %s\r\n\r\n" % (self.stream_args["stream_info"]["url"], credentials_base64_string)
                self.setup = "SETUP %s/trackID=1 RTSP/1.0\r\nCSeq: 3\r\nUser-Agent: python\r\nTransport: RTP/AVP;unicast;client_port=%s\r\nAuthorization: Basic %s\r\n\r\n" % (self.stream_args["stream_info"]["url"], self.udp_socket_port, credentials_base64_string)

                self.fhdhr.logger.info("Connecting to Socket")
                self.tcp_socket.connect((self.stream_args["stream_info"]["address"], self.stream_args["stream_info"]["port"]))

                self.fhdhr.logger.info("Sending DESCRIBE")
                self.tcp_socket.send(self.describe.encode("utf-8"))
                recst = self.tcp_socket.recv(4096).decode()
                self.fhdhr.logger.info("Got response: %s" % recst)

                self.fhdhr.logger.info("Sending SETUP")
                self.tcp_socket.send(self.setup.encode("utf-8"))
                recst = self.tcp_socket.recv(4096).decode()
                self.fhdhr.logger.info("Got response: %s" % recst)

                self.sessionid = self.sessionid(recst)
                self.fhdhr.logger.info("SessionID=%s" % self.sessionid)
                self.play = "PLAY %s RTSP/1.0\r\nCSeq: 5\r\nUser-Agent: python\r\nSession: %s\r\nRange: npt=0.000-\r\nAuthorization: Basic %s\r\n\r\n" % (self.stream_args["stream_info"]["url"], self.sessionid, credentials_base64_string)

            except Exception as exerror:
                self.fhdhr.logger.info("Closing UDP socket at %s:%s." % (self.udp_socket_address, self.udp_socket_port))
                self.udp_socket.close()
                self.fhdhr.logger.info("Closing TCP socket at %s:%s." % (self.tcp_socket_address, self.tcp_socket_port))
                self.tcp_socket.close()
                error_out = self.fhdhr.logger.lazy_exception(exerror, "806 - Tune Failed: Could Not Create Socket")
                raise TunerError(error_out)

        else: #bare RTP over UDP
            try:
                self.tcp_socket = None
                #get addr, port from rtp://ip:port
                self.address, port =self.stream_args["stream_info"]["url"].strip().split('://')[1].split(':')
                self.port = int(port)
                self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_socket.bind((self.address, self.port))
                self.udp_socket_address = self.udp_socket.getsockname()[0]
                self.udp_socket_port = self.udp_socket.getsockname()[1]
                self.udp_socket.settimeout(5)
                self.fhdhr.logger.info("RTP Created UDP socket at %s:%s." % (self.udp_socket_address, self.udp_socket_port))
            
            except Exception as exerror:
                self.fhdhr.logger.info("Closing UDP socket at %s:%s." % (self.udp_socket_address, self.udp_socket_port))
                self.udp_socket.close()
                error_out = self.fhdhr.logger.lazy_exception(exerror, "806 - Tune Failed: Could Not Create Socket")
                raise TunerError(error_out)

    def get(self):
        """
        Produce chunks of video data.
        """

        self.fhdhr.logger.info("Direct Stream of %s URL: %s" % (self.stream_args["true_content_type"], self.stream_args["stream_info"]["url"]))

        if self.tcp_socket:
            self.fhdhr.logger.info("Sending PLAY")
            self.tcp_socket.send(self.play.encode("utf-8"))

        def generate():

            try:
                while self.tuner.tuner_lock.locked():

                    packet = self.udp_socket.recv(self.stream_args["bytes_per_read"])
                    if not packet:
                        break
                    packet = RTP().fromBytearray(bytearray(packet))
                    
                    yield bytes(packet.payload)

            finally:
                self.fhdhr.logger.info("Closing UDP socket at %s:%s." % (self.udp_socket_address, self.udp_socket_port))
                self.udp_socket.close()
                if self.tcp_socket:
                    self.fhdhr.logger.info("Closing TCP socket at %s:%s." % (self.tcp_socket_address, self.tcp_socket_port))
                    self.tcp_socket.close()

        return generate()

    def get_sock_address(self):
        if self.fhdhr.config.dict["fhdhr"]["discovery_address"]:
            return self.fhdhr.config.dict["fhdhr"]["discovery_address"]
        else:
            try:
                base_url = self.stream_args["base_url"].split("://")[1].split(":")[0]
            except IndexError:
                return None
            ip_match = re.match('^' + '[\\.]'.join(['(\\d{1,3})']*4) + '$', base_url)
            ip_validate = bool(ip_match)
            if ip_validate:
                return base_url
        return None

    def sessionid(self, recst):
        """ Search session id from rtsp strings
        """
        recs = recst.split('\r\n')
        for rec in recs:
            ss = rec.split()
            if (ss[0].strip() == "Session:"):
                return int(ss[1].split(";")[0].strip())

    
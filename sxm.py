"""
SiriusXM Proxy Server

This script implements a proxy server for accessing SiriusXM radio streams. 
It handles authentication, retrieves channel information, and serves audio segments to clients.

Usage:
    python siriusxm_proxy.py [-l] [-p PORT]

Arguments:
    -l, --list      List available SiriusXM channels.
    -p PORT, --port PORT  Specify the port for the proxy server (default: 9999).

Authentication:
    SiriusXM credentials (username and password) are stored in a separate file named 'my_secrets.py' 
    in the following format:

    secrets = {
        'username': 'your_username',
        'password': 'your_password'
    }

Dependencies:
    - requests
    - base64
    - urllib.parse
    - json
    - time
    - datetime
    - sys
    - http.server
    - logging
    - argparse

"""
import argparse
import requests
import base64
import urllib.parse
import json
import time, datetime
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from my_secrets import secrets
import logging
import Adafruit_IO


# Better logging solution
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Data storage via Adafruit IO
aio = Adafruit_IO.Client(secrets['aio_user'], secrets['aio_key'])
now_playing_feed = aio.feeds('now-playing') # Assumes the feed exists

class SiriusXM:
    """
    Handles SiriusXM authentication and stream retrieval.

    Attributes:
        USER_AGENT (str): User-Agent string for HTTP requests.
        REST_FORMAT (str): Base URL for SiriusXM REST API.
        LIVE_PRIMARY_HLS (str): Base URL for HLS streams.

    Methods:
        log(message, level): Logs messages with specified level.
        is_logged_in(): Checks if user is logged in.
        is_session_authenticated(): Checks if session is authenticated.
        get(method, params, authenticate): Makes a GET request to the SiriusXM API.
        post(method, postdata, authenticate): Makes a POST request to the SiriusXM API.
        login(): Performs login to SiriusXM.
        authenticate(): Authenticates the session.
        get_sxmak_token(): Retrieves the SXMAKTOKEN from cookies.
        get_gup_id(): Retrieves the gupId from cookies.
        get_playlist_url(guid, channel_id, use_cache, max_attempts): Retrieves the playlist URL for a channel.
        get_playlist_variant_url(url): Retrieves the playlist variant URL.
        get_playlist(name, use_cache): Retrieves the HLS playlist for a channel.
        get_segment(path, max_attempts): Retrieves a segment of the audio stream.
        get_channels(): Retrieves the list of available channels.
        get_channel(name): Retrieves channel information by name or ID.
    """
    USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/604.5.6 (KHTML, like Gecko) Version/11.0.3 Safari/604.5.6'
    REST_FORMAT = 'https://player.siriusxm.com/rest/v2/experience/modules/{}'
    LIVE_PRIMARY_HLS = 'https://siriusxm-priprodlive.akamaized.net'

    def __init__(self, username, password):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.USER_AGENT})
        self.username = username
        self.password = password
        self.playlists = {}
        self.channels = None

    # Wrapper for logging may not be needed
    def log(self, message, level="DEBUG"):
        if level == "DEBUG":
            logging.debug(message)
        elif level == "INFO": # and so on for other levels
            logging.info(message)
        elif level == "ERROR":
            logging.error(message)

    def is_logged_in(self):
        return 'SXMAUTHNEW' in self.session.cookies

    def is_session_authenticated(self):
        return 'AWSALB' in self.session.cookies and 'JSESSIONID' in self.session.cookies

    def get(self, method, params, authenticate=True):
        if authenticate and not self.is_session_authenticated() and not self.authenticate():
            self.log('Unable to authenticate')
            return None

        res = self.session.get(self.REST_FORMAT.format(method), params=params)
        if res.status_code != 200:
            self.log('Received status code {} for method \'{}\''.format(res.status_code, method))
            return None

        try:
            return res.json()
        except ValueError:
            self.log('Error decoding json for method \'{}\''.format(method))
            return None

    def post(self, method, postdata, authenticate=True):
        if authenticate and not self.is_session_authenticated() and not self.authenticate():
            self.log('Unable to authenticate')
            return None
        req = 'wassup'
        print(self.REST_FORMAT.format(method))
        res = self.session.post(self.REST_FORMAT.format(method), data=json.dumps(postdata))
        if res.status_code != 200:
            self.log('Received status code {} for method \'{}\''.format(res.status_code, method))
            return None

        try:
            return res.json()
        except ValueError:
            self.log('Error decoding json for method \'{}\''.format(method))
            return None

    def login(self):
        postdata = {
            'moduleList': {
                'modules': [{
                    'moduleRequest': {
                        'resultTemplate': 'web',
                        'deviceInfo': {
                            'osVersion': 'Mac',
                            'platform': 'Web',
                            'sxmAppVersion': '3.1802.10011.0',
                            'browser': 'Safari',
                            'browserVersion': '11.0.3',
                            'appRegion': 'US',
                            'deviceModel': 'K2WebClient',
                            'clientDeviceId': 'null',
                            'player': 'html5',
                            'clientDeviceType': 'web',
                        },
                        'standardAuth': {
                            'username': self.username,
                            'password': self.password,
                        },
                    },
                }],
            },
        }
        data = self.post('modify/authentication', postdata, authenticate=False)
        if not data:
            return False

        try:
            return data['ModuleListResponse']['status'] == 1 and self.is_logged_in()
        except KeyError:
            self.log('Error decoding json response for login')
            return False

    def authenticate(self):
        if not self.is_logged_in() and not self.login():
            self.log('Unable to authenticate because login failed')
            return False

        postdata = {
            'moduleList': {
                'modules': [{
                    'moduleRequest': {
                        'resultTemplate': 'web',
                        'deviceInfo': {
                            'osVersion': 'Mac',
                            'platform': 'Web',
                            'clientDeviceType': 'web',
                            'sxmAppVersion': '3.1802.10011.0',
                            'browser': 'Safari',
                            'browserVersion': '11.0.3',
                            'appRegion': 'US',
                            'deviceModel': 'K2WebClient',
                            'player': 'html5',
                            'clientDeviceId': 'null'
                        }
                    }
                }]
            }
        }
        data = self.post('resume?OAtrial=false', postdata, authenticate=False)
        if not data:
            return False

        try:
            return data['ModuleListResponse']['status'] == 1 and self.is_session_authenticated()
        except KeyError:
            self.log('Error parsing json response for authentication')
            return False

    def get_sxmak_token(self):
        try:
            return self.session.cookies['SXMAKTOKEN'].split('=', 1)[1].split(',', 1)[0]
        except (KeyError, IndexError):
            return None

    def get_gup_id(self):
        try:
            return json.loads(urllib.parse.unquote(self.session.cookies['SXMDATA']))['gupId']
        except (KeyError, ValueError):
            return None

    def get_playlist_info(self, guid, channel_id, use_cache=False, max_attempts=5):

        params = {
            'assetGUID': guid,
            'ccRequestType': 'AUDIO_VIDEO',
            'channelId': channel_id,
            'hls_output_mode': 'custom',
            'marker_mode': 'all_separate_cue_points',
            'result-template': 'web',
            'time': int(round(time.time() * 1000.0)),
            'timestamp': datetime.datetime.utcnow().isoformat('T') + 'Z'
        }
        data = self.get('tune/now-playing-live', params)
        if not data:
            return None

        # get status
        try:
            status = data['ModuleListResponse']['status']
            message = data['ModuleListResponse']['messages'][0]['message']
            message_code = data['ModuleListResponse']['messages'][0]['code']
        except (KeyError, IndexError):
            self.log('Error parsing json response for playlist')
            return None

        # login if session expired
        if message_code == 201 or message_code == 208:
            if max_attempts > 0:
                self.log('Session expired, logging in and authenticating')
                if self.authenticate():
                    self.log('Successfully authenticated')
                else:
                    self.log('Failed to authenticate')
                    return None
            else:
                self.log('Reached max attempts for playlist')
                return None
        elif message_code != 100:
            self.log('Received error {} {}'.format(message_code, message))
            return None

        # get m3u8 url
        try:
            playlists = data['ModuleListResponse']['moduleList']['modules'][0]['moduleResponse']['liveChannelData']['hlsAudioInfos']
            mydata = data['ModuleListResponse']['moduleList']['modules'][0]['moduleResponse']['liveChannelData']
            self.log(mydata['markerLists'][3]['markers'][-1]['cut']['title'])
        except (KeyError, IndexError):
            self.log('Error parsing json response for playlist')
            return None
        for playlist_info in playlists:
            if playlist_info['size'] == 'LARGE':
                playlist_url = playlist_info['url'].replace('%Live_Primary_HLS%', self.LIVE_PRIMARY_HLS)
                self.playlists[channel_id] = self.get_playlist_variant_url(playlist_url)
                return data['ModuleListResponse']['moduleList']['modules'][0]['moduleResponse']['liveChannelData']

        return None

    def get_song_info(self, guid, channel_id, full_data=False):
        params = {
            'assetGUID': guid,
            'ccRequestType': 'AUDIO_VIDEO',
            'channelId': channel_id,
            'hls_output_mode': 'custom',
            'marker_mode': 'all_separate_cue_points',
            'result-template': 'web',
            'time': int(round(time.time() * 1000.0)),
            'timestamp': datetime.datetime.utcnow().isoformat('T') + 'Z'
        }
        data = self.get('tune/now-playing-live', params)
        if not data:
            return None

        # get song info
        musicdata = data['ModuleListResponse']['moduleList']['modules'][0]['moduleResponse']['liveChannelData']
        station = musicdata['markerLists'][0]['markers'][0]['episode']['longTitle']
        logging.info("STATION: {}".format(station))
        logging.info("SONG: {}".format(musicdata['markerLists'][3]['markers'][-1]['cut']['title']))
        logging.info("ARTIST: {}".format(musicdata['markerLists'][3]['markers'][-1]['cut']['artists'][0]['name']))

        # post to Adafruit_IO
        try:
            data_to_send = {
                'title': musicdata['markerLists'][3]['markers'][-1]['cut']['title'],
                'artist': musicdata['markerLists'][3]['markers'][-1]['cut']['artists'][0]['name'],
                'station': station,
                'playing': True,
            }
            aio.send_data(now_playing_feed.key, json.dumps(data_to_send))
            logging.debug('Data successfully sent to Adafruit')
        except Adafruit_IO.RequestError as e:
            logging.error("Error updating Adafruit-IO: {}".format(e))

        if full_data:
            return data
        else:
            return None        

    def get_playlist_url(self, guid, channel_id, use_cache=True, max_attempts=5):
        # Get song info - this adds a SiriusXM call
        self.get_song_info(guid, channel_id)

        if use_cache and channel_id in self.playlists:
             return self.playlists[channel_id]

        params = {
            'assetGUID': guid,
            'ccRequestType': 'AUDIO_VIDEO',
            'channelId': channel_id,
            'hls_output_mode': 'custom',
            'marker_mode': 'all_separate_cue_points',
            'result-template': 'web',
            'time': int(round(time.time() * 1000.0)),
            'timestamp': datetime.datetime.utcnow().isoformat('T') + 'Z'
        }
        data = self.get('tune/now-playing-live', params)
        if not data:
            return None


        # get status
        try:
            status = data['ModuleListResponse']['status']
            message = data['ModuleListResponse']['messages'][0]['message']
            message_code = data['ModuleListResponse']['messages'][0]['code']
        except (KeyError, IndexError):
            self.log('Error parsing json response for playlist')
            return None

        # login if session expired
        if message_code == 201 or message_code == 208:
            if max_attempts > 0:
                self.log('Session expired, logging in and authenticating')
                if self.authenticate():
                    self.log('Successfully authenticated')
                    return self.get_playlist_url(guid, channel_id, use_cache, max_attempts - 1)
                else:
                    self.log('Failed to authenticate')
                    return None
            else:
                self.log('Reached max attempts for playlist')
                return None
        elif message_code != 100:
            self.log('Received error {} {}'.format(message_code, message))
            return None

        # get m3u8 url
        try:
            playlists = data['ModuleListResponse']['moduleList']['modules'][0]['moduleResponse']['liveChannelData']['hlsAudioInfos']

        except (KeyError, IndexError):
            self.log('Error parsing json response for playlist')
            return None
        for playlist_info in playlists:
            if playlist_info['size'] == 'LARGE':
                playlist_url = playlist_info['url'].replace('%Live_Primary_HLS%', self.LIVE_PRIMARY_HLS)
                self.playlists[channel_id] = self.get_playlist_variant_url(playlist_url)
                return self.playlists[channel_id]

        return None

    def get_playlist_variant_url(self, url):
        params = {
            'token': self.get_sxmak_token(),
            'consumer': 'k2',
            'gupId': self.get_gup_id(),
        }
        res = self.session.get(url, params=params)

        if res.status_code != 200:
            self.log('Received status code {} on playlist variant retrieval'.format(res.status_code))
            return None
        
        for x in res.text.split('\n'):
            if x.rstrip().endswith('.m3u8'):
                # first variant should be 256k one
                return '{}/{}'.format(url.rsplit('/', 1)[0], x.rstrip())
        
        return None

    def get_playlist(self, name, use_cache=True):
        guid, channel_id = self.get_channel(name)
        if not guid or not channel_id:
            self.log('No channel for {}'.format(name))
            return None

        # inefficient hack to get title

        url = self.get_playlist_url(guid, channel_id, use_cache)
        params = {
            'token': self.get_sxmak_token(),
            'consumer': 'k2',
            'gupId': self.get_gup_id(),
        }
        res = self.session.get(url, params=params)

        if res.status_code == 403:
            self.log('Received status code 403 on playlist, renewing session')
            return self.get_playlist(name, False)

        if res.status_code != 200:
            self.log('Received status code {} on playlist variant'.format(res.status_code))
            return None

        # add base path to segments
        base_url = url.rsplit('/', 1)[0]
        base_path = base_url[8:].split('/', 1)[1]
        lines = res.text.split('\n')
        for x in range(len(lines)):
            if lines[x].rstrip().endswith('.aac'):
                lines[x] = '{}/{}'.format(base_path, lines[x])
        return '\n'.join(lines)

    def get_segment(self, path, max_attempts=5):
        url = '{}/{}'.format(self.LIVE_PRIMARY_HLS, path)
        params = {
            'token': self.get_sxmak_token(),
            'consumer': 'k2',
            'gupId': self.get_gup_id(),
        }
        res = self.session.get(url, params=params)

        if res.status_code == 403:
            if max_attempts > 0:
                self.log('Received status code 403 on segment, renewing session')
                self.get_playlist(path.split('/', 2)[1], False)
                return self.get_segment(path, max_attempts - 1)
            else:
                self.log('Received status code 403 on segment, max attempts exceeded')
                return None

        if res.status_code != 200:
            self.log('Received status code {} on segment'.format(res.status_code))
            return None

        return res.content
    
    def get_channels(self):
        # download channel list if necessary
        if not self.channels:
            postdata = {
                'moduleList': {
                    'modules': [{
                        'moduleArea': 'Discovery',
                        'moduleType': 'ChannelListing',
                        'moduleRequest': {
                            'consumeRequests': [],
                            'resultTemplate': 'responsive',
                            'alerts': [],
                            'profileInfos': []
                        }
                    }]
                }
            }
            data = self.post('get', postdata)
            if not data:
                self.log('Unable to get channel list')
                return (None, None)

            try:
                self.channels = data['ModuleListResponse']['moduleList']['modules'][0]['moduleResponse']['contentData']['channelListing']['channels']
            except (KeyError, IndexError):
                self.log('Error parsing json response for channels')
                return []
        return self.channels

    
    def get_channel(self, name):
        name = name.lower()
        for x in self.get_channels():
            if x.get('name', '').lower() == name or x.get('channelId', '').lower() == name or x.get('siriusChannelNumber') == name:
                return (x['channelGuid'], x['channelId'])
        return (None, None)

def make_sirius_handler(sxm):
    """
    Creates a request handler class for the HTTP server.

    Args:
        sxm (SiriusXM): An instance of the SiriusXM class.

    Returns:
        SiriusHandler: A class derived from BaseHTTPRequestHandler.
    """
    class SiriusHandler(BaseHTTPRequestHandler):
        """
        Handles HTTP requests for the proxy server.

        Attributes:
            HLS_AES_KEY (bytes): AES decryption key for HLS segments.

        Methods:
            do_GET(): Handles GET requests for playlists and segments.
        """
        HLS_AES_KEY = base64.b64decode('0Nsco7MAgxowGvkUT8aYag==')

        def do_GET(self):
            if self.path.endswith('.m3u8'):
                data = sxm.get_playlist(self.path.rsplit('/', 1)[1][:-5])
                logging.debug("do_GET wants: {}".format(self.path.rsplit('/', 1)[1][:-5]))
                if data:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/x-mpegURL')
                    self.end_headers()
                    self.wfile.write(bytes(data, 'utf-8'))
                else:
                    self.send_response(500)
                    self.end_headers()
            elif self.path.endswith('.aac'):
                data = sxm.get_segment(self.path[1:])
                logging.debug("do_GET wants {}".format(self.path[1:]))
                if data:
                    self.send_response(200)
                    self.send_header('Content-Type', 'audio/x-aac')
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self.send_response(500)
                    self.end_headers()
            elif self.path.endswith('/key/1'):
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(self.HLS_AES_KEY)
            else:
                self.send_response(500)
                self.end_headers()
    return SiriusHandler

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SiriusXM proxy')
    #parser.add_argument('username')
    #parser.add_argument('password')
    parser.add_argument('-l', '--list', required=False, action='store_true', default=False)
    parser.add_argument('-p', '--port', required=False, default=9999, type=int)
    args = vars(parser.parse_args())
    
    sxm = SiriusXM(secrets['username'], secrets['password'])
    #sxm = SiriusXM(args['username'], args['password'])
    if args['list']:
        channels = list(sorted(sxm.get_channels(), key=lambda x: (not x.get('isFavorite', False), int(x.get('siriusChannelNumber', 9999)))))
        
        l1 = max(len(x.get('channelId', '')) for x in channels)
        l2 = max(len(str(x.get('siriusChannelNumber', 0))) for x in channels)
        l3 = max(len(x.get('name', '')) for x in channels)
        print('{} | {} | {}'.format('ID'.ljust(l1), 'Num'.ljust(l2), 'Name'.ljust(l3)))
        for channel in channels:
            cid = channel.get('channelId', '').ljust(l1)[:l1]
            cnum = str(channel.get('siriusChannelNumber', '??')).ljust(l2)[:l2]
            cname = channel.get('name', '??').ljust(l3)[:l3]
            print('{} | {} | {}'.format(cid, cnum, cname))
    else:
        httpd = HTTPServer(('', args['port']), make_sirius_handler(sxm))
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        httpd.server_close()

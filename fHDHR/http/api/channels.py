from flask import request, redirect, Response
import urllib.parse
import json


class Channels():
    endpoints = ["/api/channels"]
    endpoint_name = "api_channels"

    def __init__(self, fhdhr):
        self.fhdhr = fhdhr

    def __call__(self, *args):
        return self.get(*args)

    def get(self, *args):

        method = request.args.get('method', default=None, type=str)
        redirect_url = request.args.get('redirect', default=None, type=str)

        if method == "scan":
            self.fhdhr.device.station_scan.scan()

        if method == "list":
            channel_list = self.fhdhr.device.channels.get_channels()
            channel_list_json = json.dumps(channel_list, indent=4)

            return Response(status=200,
                            response=channel_list_json,
                            mimetype='application/json')

        else:
            return "Invalid Method"

        if redirect_url:
            return redirect(redirect_url + "?retmessage=" + urllib.parse.quote("%s Success" % method))
        else:
            if method == "scan":
                return redirect('/lineup_status.json')
            else:
                return "%s Success" % method

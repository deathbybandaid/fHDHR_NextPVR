from flask import Response, request, redirect, abort, stream_with_context
import urllib.parse

from fHDHR.exceptions import TunerError


class Watch():
    """Methods to create xmltv.xml"""
    endpoints = ["/api/watch"]
    endpoint_name = "api_watch"

    def __init__(self, fhdhr):
        self.fhdhr = fhdhr

    def __call__(self, *args):
        return self.get(*args)

    def get(self, *args):

        full_url = request.url

        method = request.args.get('method', default=self.fhdhr.config.dict["fhdhr"]["stream_type"], type=str)

        tuner_number = request.args.get('tuner', None, type=str)

        redirect_url = request.args.get('redirect', default=None, type=str)

        if method in ["direct", "ffmpeg", "vlc"]:

            channel_number = request.args.get('channel', None, type=str)
            if not channel_number:
                return "Missing Channel"

            channel_list = [self.fhdhr.device.channels.list[x].dict["number"] for x in list(self.fhdhr.device.channels.list.keys())]
            if channel_number not in channel_list:
                response = Response("Not Found", status=404)
                response.headers["X-fHDHR-Error"] = "801 - Unknown Channel"
                self.fhdhr.logger.error(response.headers["X-fHDHR-Error"])
                abort(response)

            duration = request.args.get('duration', default=0, type=int)

            transcode = request.args.get('transcode', default=None, type=str)
            valid_transcode_types = [None, "heavy", "mobile", "internet720", "internet480", "internet360", "internet240"]
            if transcode not in valid_transcode_types:
                response = Response("Service Unavailable", status=503)
                response.headers["X-fHDHR-Error"] = "802 - Unknown Transcode Profile"
                self.fhdhr.logger.error(response.headers["X-fHDHR-Error"])
                abort(response)

            stream_args = {
                            "channel": channel_number,
                            "method": method,
                            "duration": duration,
                            "transcode": transcode,
                            "accessed": full_url,
                            }

            try:
                if not tuner_number:
                    tunernum = self.fhdhr.device.tuners.first_available()
                else:
                    tunernum = self.fhdhr.device.tuners.tuner_grab(tuner_number)
            except TunerError as e:
                self.fhdhr.logger.info("A %s stream request for channel %s was rejected due to %s"
                                       % (stream_args["method"], str(stream_args["channel"]), str(e)))
                response = Response("Service Unavailable", status=503)
                response.headers["X-fHDHR-Error"] = str(e)
                self.fhdhr.logger.error(response.headers["X-fHDHR-Error"])
                abort(response)
            tuner = self.fhdhr.device.tuners.tuners[int(tunernum)]

            try:
                stream_args = self.fhdhr.device.tuners.get_stream_info(stream_args)
            except TunerError as e:
                self.fhdhr.logger.info("A %s stream request for channel %s was rejected due to %s"
                                       % (stream_args["method"], str(stream_args["channel"]), str(e)))
                response = Response("Service Unavailable", status=503)
                response.headers["X-fHDHR-Error"] = str(e)
                self.fhdhr.logger.error(response.headers["X-fHDHR-Error"])
                tuner.close()
                abort(response)

            self.fhdhr.logger.info("Tuner #" + str(tunernum) + " to be used for stream.")
            tuner.set_status(stream_args)

            if stream_args["method"] == "direct":
                return Response(tuner.get_stream(stream_args, tuner), content_type=stream_args["content_type"], direct_passthrough=True)
            elif stream_args["method"] in ["ffmpeg", "vlc"]:
                return Response(stream_with_context(tuner.get_stream(stream_args, tuner)), mimetype=stream_args["content_type"])

        elif method == "close":

            if not tuner_number or int(tuner_number) not in list(self.fhdhr.device.tuners.tuners.keys()):
                return "%s Invalid tuner" % str(tuner_number)

            tuner = self.fhdhr.device.tuners.tuners[int(tuner_number)]
            tuner.close()

        else:
            return "%s Invalid Method" % method

        if redirect_url:
            return redirect(redirect_url + "?retmessage=" + urllib.parse.quote("%s Success" % method))
        else:
            return "%s Success" % method

from flask import Response, request, stream_with_context, abort

from fHDHR.exceptions import TunerError


class Tuner():
    endpoints = ['/tuner<tuner_number>/<channel>']
    endpoint_name = "tuner"

    def __init__(self, fhdhr):
        self.fhdhr = fhdhr

    def __call__(self, tuner_number, channel, *args):
        return self.get(tuner_number, channel, *args)

    def get(self, tuner_number, channel, *args):

        full_url = request.url

        if channel.startswith("v"):
            channel_number = channel.replace('v', '')
        elif channel.startswith("ch"):
            channel_freq = channel.replace('ch', '').split("-")[0]
            subchannel = 0
            if "-" in channel:
                subchannel = channel.replace('ch', '').split("-")[1]
            self.fhdhr.logger.error("Not Implemented %s-%s" % (str(channel_freq), str(subchannel)))
            abort(501, "Not Implemented %s-%s" % (str(channel_freq), str(subchannel)))

        channel_list = [self.fhdhr.device.channels.list[x].dict["number"] for x in list(self.fhdhr.device.channels.list.keys())]
        if channel_number not in channel_list:
            response = Response("Not Found", status=404)
            response.headers["X-fHDHR-Error"] = "801 - Unknown Channel"
            self.fhdhr.logger.error(response.headers["X-fHDHR-Error"])
            abort(response)

        method = request.args.get('method', default=self.fhdhr.config.dict["fhdhr"]["stream_type"], type=str)
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

        """
        try:
            if stream_args["method"] == "direct":
                return Response(tuner.get_stream(stream_args, tuner), content_type=stream_args["content_type"], direct_passthrough=True)
            elif stream_args["method"] in ["ffmpeg", "vlc"]:
                return Response(stream_with_context(tuner.get_stream(stream_args, tuner)), mimetype=stream_args["content_type"])
        except TunerError as e:
            tuner.close()
            self.fhdhr.logger.info("A %s stream request for channel %s failed due to %s"
                                   % (stream_args["method"], str(stream_args["channel"]), str(e)))
            response = Response("Service Unavailable", status=503)
            response.headers["X-fHDHR-Error"] = str(e)
            abort(response)
        """

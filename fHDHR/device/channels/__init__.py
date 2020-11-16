import datetime
from collections import OrderedDict

from fHDHR.tools import hours_between_datetime

from .channel import Channel
from .chan_ident import Channel_IDs


class Channels():

    def __init__(self, fhdhr, origin):
        self.fhdhr = fhdhr

        self.origin = origin

        self.id_system = Channel_IDs(fhdhr)

        self.list = {}
        self.list_update_time = None
        self.get_db_channels()
        self.get_channels()

    def get_db_channels(self):
        channel_ids = self.fhdhr.db.get_fhdhr_value("channels", "IDs") or []
        for channel_id in channel_ids:
            channel_obj = Channel(self.fhdhr, self.id_system, channel_id)
            channel_id = channel_obj.dict["fhdhr_id"]
            self.list[channel_id] = channel_obj

    def get_channels(self, forceupdate=False):
        """Pull Channels from origin.

        Output a list.

        Don't pull more often than 12 hours.
        """

        updatelist = False
        if not self.list_update_time:
            updatelist = True
        elif hours_between_datetime(self.list_update_time, datetime.datetime.now()) > 12:
            updatelist = True
        elif forceupdate:
            updatelist = True

        if updatelist:
            channel_dict_list = self.origin.get_channels()
            channel_dict_list = self.verify_channel_info(channel_dict_list)
            for channel_info in channel_dict_list:
                channel_obj = Channel(self.fhdhr, origin_id=channel_info["id"])
                channel_id = channel_obj.dict["fhdhr_id"]
                channel_obj.basics(channel_info)
                self.list[channel_id] = channel_obj

            if not self.list_update_time:
                self.fhdhr.logger.info("Found " + str(len(self.list)) + " channels for " + str(self.fhdhr.config.dict["main"]["servicename"]))
            self.list_update_time = datetime.datetime.now()

        channel_list = []
        for chan_obj in list(self.list.keys()):
            channel_list.append(self.list[chan_obj].dict)
        return channel_list

    def get_station_list(self, base_url):
        station_list = []

        for c in self.get_channels():
            station_list.append({
                                 'GuideNumber': c['number'],
                                 'GuideName': c['name'],
                                 'Tags': ",".join(c['tags']),
                                 'URL': self.get_fhdhr_stream_url(base_url, c['number']),
                                })
        return station_list

    def get_channel_stream(self, channel_number):
        channel_id = (self.list[channel_id].dict["fhdhr_id"] for channel_id in list(self.list.keys()) if self.list[channel_id].dict["number"] == channel_number) or None
        if not channel_id:
            return None
        return self.origin.get_channel_stream(self.list[channel_id].dict)

    def get_station_total(self):
        return len(list(self.list.keys()))

    def get_channel_dict(self, keyfind, valfind):
        chanlist = self.get_channels()
        return next(item for item in chanlist if item[keyfind] == valfind)

    def get_fhdhr_stream_url(self, base_url, channel_number):
        return ('%s/auto/v%s' %
                (base_url,
                 channel_number))

    def verify_channel_info(self, channel_dict_list):
        """Some Channel Information is Critical"""
        cleaned_channel_dict_list = []
        for station_item in channel_dict_list:

            if "id" not in list(station_item.keys()):
                station_item["id"] = station_item["name"]

            cleaned_channel_dict_list.append(station_item)
        return cleaned_channel_dict_list

    def channel_order(self):
        """Verify the Channel Order"""
        self.list = OrderedDict(sorted(self.list.items()))

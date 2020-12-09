import datetime

from fHDHR.exceptions import EPGSetupError


class tvtvEPG():

    def __init__(self, fhdhr, channels):
        self.fhdhr = fhdhr

        self.channels = channels

    @property
    def postalcode(self):
        if self.fhdhr.config.dict["tvtv"]["postalcode"]:
            return self.fhdhr.config.dict["tvtv"]["postalcode"]
        try:
            postalcode_url = 'http://ipinfo.io/json'
            postalcode_req = self.fhdhr.web.session.get(postalcode_url)
            data = postalcode_req.json()
            postalcode = data["postal"]
        except Exception as e:
            raise EPGSetupError("Unable to automatically optain postalcode: " + str(e))
            postalcode = None
        return postalcode

    @property
    def lineup_id(self):
        lineup_id_url = "https://www.tvtv.us/tvm/t/tv/v4/lineups?postalCode=%s" % self.postalcode
        if self.fhdhr.config.dict["tvtv"]["lineuptype"]:
            lineup_id_url += "&lineupType=%s" % self.fhdhr.config.dict["tvtv"]["lineuptype"]
        lineup_id_req = self.fhdhr.web.session.get(lineup_id_url)
        data = lineup_id_req.json()
        lineup_id = data[0]["lineupID"]
        return lineup_id

    def update_epg(self):
        programguide = {}

        # Make a date range to pull
        todaydate = datetime.date.today()
        dates_to_pull = []
        for x in range(0, 6):
            datesdict = {
                        "start": todaydate + datetime.timedelta(days=x),
                        "stop": todaydate + datetime.timedelta(days=x+1)
                        }
            dates_to_pull.append(datesdict)

        self.remove_stale_cache(todaydate)

        cached_items = self.get_cached(dates_to_pull)
        print(cached_items[0])

        return programguide

    def get_cached(self, dates_to_pull):
        for datesdict in dates_to_pull:
            starttime = "%sT00%3A00%3A00.000Z" % str(datesdict["start"])
            stoptime = "%sT00%3A00%3A00.000Z" % str(datesdict["stop"])
            url = "https://www.tvtv.us/tvm/t/tv/v4/lineups/%s/listings/grid?start=%s&%s" % (self.lineup_id, starttime, stoptime)
            self.get_cached_item(str(starttime), url)
        cache_list = self.fhdhr.db.get_cacheitem_value("cache_list", "offline_cache", "tvtv") or []
        return [self.fhdhr.db.get_cacheitem_value(x, "offline_cache", "tvtv") for x in cache_list]

    def get_cached_item(self, cache_key, url):
        cacheitem = self.fhdhr.db.get_cacheitem_value(cache_key, "offline_cache", "tvtv")
        if cacheitem:
            self.fhdhr.logger.info('FROM CACHE:  ' + str(cache_key))
            return cacheitem
        else:
            self.fhdhr.logger.info('Fetching:  ' + url)
            try:
                resp = self.fhdhr.web.session.get(url)
            except self.fhdhr.web.exceptions.HTTPError:
                self.fhdhr.logger.info('Got an error!  Ignoring it.')
                return
            result = resp.json()

            self.fhdhr.db.set_cacheitem_value(cache_key, "offline_cache", result, "tvtv")
            cache_list = self.fhdhr.db.get_cacheitem_value("cache_list", "offline_cache", "tvtv") or []
            cache_list.append(cache_key)
            self.fhdhr.db.set_cacheitem_value("cache_list", "offline_cache", cache_list, "tvtv")

    def remove_stale_cache(self, todaydate):
        cache_list = self.fhdhr.db.get_cacheitem_value("cache_list", "offline_cache", "tvtv") or []
        cache_to_kill = []
        for cacheitem in cache_list:
            cachedate = datetime.datetime.strptime(str(cacheitem), "%Y-%m-%d")
            todaysdate = datetime.datetime.strptime(str(todaydate), "%Y-%m-%d")
            if cachedate < todaysdate:
                cache_to_kill.append(cacheitem)
                self.fhdhr.db.delete_cacheitem_value(cacheitem, "offline_cache", "tvtv")
                self.fhdhr.logger.info('Removing stale cache:  ' + str(cacheitem))
        self.fhdhr.db.set_cacheitem_value("cache_list", "offline_cache", [x for x in cache_list if x not in cache_to_kill], "tvtv")

    def clear_cache(self):
        cache_list = self.fhdhr.db.get_cacheitem_value("cache_list", "offline_cache", "tvtv") or []
        for cacheitem in cache_list:
            self.fhdhr.db.delete_cacheitem_value(cacheitem, "offline_cache", "tvtv")
            self.fhdhr.logger.info('Removing cache:  ' + str(cacheitem))
        self.fhdhr.db.delete_cacheitem_value("cache_list", "offline_cache", "tvtv")

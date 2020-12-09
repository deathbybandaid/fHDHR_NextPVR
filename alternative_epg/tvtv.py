

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
            lineup_id_url += "&lineuptype=%s" % self.fhdhr.config.dict["tvtv"]["lineuptype"]
        print(lineup_id_url)
        lineup_id_req = self.fhdhr.web.session.get(lineup_id_url)
        data = lineup_id_req.json()
        lineup_id = data[0]["lineupID"]
        return lineup_id

    def update_epg(self):
        programguide = {}
        print(self.lineup_id)
        return programguide

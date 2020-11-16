

class Channel():

    def __init__(self, fhdhr, id_system, origin_id=None, channel_id=None):
        self.fhdhr = fhdhr

        self.id_system = id_system

        if not channel_id:
            if origin_id:
                print("a")
                channel_id = id_system.get(origin_id)
                print(channel_id)
            else:
                print("b")
                channel_id = id_system.assign()
                print(channel_id)
        self.dict = self.fhdhr.db.get_channel_value(channel_id, "info") or self.create_empty_channel(channel_id)
        self.fhdhr.db.set_channel_value(channel_id, "info", self.dict)

    def basics(self, channel_info):
        """Some Channel Information is Critical"""

        if "name" not in list(channel_info.keys()):
            channel_info["name"] = self.dict["fhdhr_id"]

        if "callsign" not in list(channel_info.keys()):
            channel_info["callsign"] = channel_info["name"]

        if "id" not in list(channel_info.keys()):
            channel_info["id"] = channel_info["name"]

        if "tags" not in list(channel_info.keys()):
            channel_info["tags"] = []

        if "number" not in list(channel_info.keys()):
            channel_info["number"] = self.id_system.get_number(channel_info["id"])
        else:
            channel_info["number"] = str(float(channel_info["number"]))

        self.id_system.set_number(self.dict["fhdhr_id"], channel_info["number"])

        self.append_channel_info(channel_info)

    def create_empty_channel(self, channel_id):
        return {
                "fhdhr_id": channel_id,
                "origin_id": None,
                "name": None,
                "callsign": None,
                "number": None,
                "tags": [],
                "enabled": True
                }

    def destroy(self):
        self.fhdhr.db.delete_channel_value(self.dict["fhdhr_id"], "info")
        channel_ids = self.fhdhr.db.get_fhdhr_value("channels", "IDs") or []
        if self.dict["fhdhr_id"] in channel_ids:
            channel_ids.remove(self.dict["fhdhr_id"])
        self.fhdhr.db.set_fhdhr_value("channels", "IDs", channel_ids)

    def append_channel_info(self, channel_info):
        for chankey in list(channel_info.keys()):
            self.dict[chankey] = channel_info[chankey]
        self.fhdhr.db.set_channel_value(self.dict["fhdhr_id"], "info", self.dict)

    def __getattr__(self, name):
        ''' will only get called for undefined attributes '''
        if name in list(self.dict.keys()):
            return self.dict[name]

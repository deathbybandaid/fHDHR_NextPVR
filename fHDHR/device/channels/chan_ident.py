import uuid


class Channel_IDs():
    def __init__(self, fhdhr):
        self.fhdhr = fhdhr

    def get(self, origin_id):
        existing_ids = self.fhdhr.db.get_fhdhr_value("channels", "IDs") or []
        existing_channel_info = [self.fhdhr.db.get_channel_value(channel_id, "info") or {} for channel_id in existing_ids]
        for existing_channel in existing_channel_info:
            if existing_channel["origin_id"] == origin_id:
                return existing_channel["fhdhr_id"]
        return self.assign()

    def assign(self):
        existing_ids = self.fhdhr.db.get_fhdhr_value("channels", "IDs") or []
        unique_id = None
        while not unique_id and unique_id in existing_ids:
            unique_id = uuid.uuid4()
        existing_ids.append(unique_id)
        self.fhdhr.db.set_fhdhr_value("channels", "IDs", existing_ids)
        return unique_id

    def get_number(self, channel_id):
        existing_ids = self.fhdhr.db.get_fhdhr_value("channels", "IDs") or []
        existing_channel_info = [self.fhdhr.db.get_channel_value(channel_id, "info") or {} for channel_id in existing_ids]
        cnumber = (existing_channel["number"] for existing_channel in existing_channel_info if existing_channel["fhdhr_id"] == channel_id) or None
        if cnumber:
            return cnumber

        used_numbers = [existing_channel["number"] for existing_channel in existing_channel_info]
        for i in range(1000, 2000):
            if str(float(i)) not in used_numbers:
                break
        return str(float(i))

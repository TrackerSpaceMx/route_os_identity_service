from database.operations_db import OperationsDB

class ProfilesProcess:
    def __init__(self):
        self._dbOperations = OperationsDB()
        self.LOCKED_RULES = {"panic", "battery_disconnected", "jammer_detected"}
        self.RULE_DEFS = {
            "panic":                {"category": "security"},
            "battery_disconnected": {"category": "security"},
            "jammer_detected":      {"category": "security"},
            "risk_zone":            {"category": "route_zones"},
            "signal_loss":          {"category": "route_zones"},
            "route_deviation":      {"category": "route_zones"},
            "restricted_stop":      {"category": "route_zones"},
            "authorized_stop":      {"category": "route_zones"},
            "restricted_hours":     {"category": "route_zones"},
            "unload_dwell":         {"category": "operations"},
            "rest_dwell":           {"category": "operations"},
            "suspicious_call":      {"category": "operations"},
        }

    async def protocol_profile_creation(self, account_id, user_id, payload: dict):
        try:
            for rule in payload["rules"]:
                if rule["rule_type"] in self.LOCKED_RULES and not rule["is_enabled"]:
                    return "LOCKED_RULE"

            return await self._dbOperations.create_protocol_profile(
                account_id, user_id, payload, self.RULE_DEFS, self.LOCKED_RULES
            )
        except Exception as err:
            print("Error creating protocol profile:", err)
            return False

    async def show_protocols(self,account_id):
        try:
            profiles = await self._dbOperations.get_protocol_profiles_from_table(account_id)
            return profiles
        except Exception as err:
            print("Error getting the protocols: ",err)
            return None

from database.operations_db import OperationsDB

class MonitoringProcess:
    def __init__(self):
        self._dbOperations = OperationsDB()


    async def get_monitoring_information(self,account_id):
        try:
            monitoring_response = await self._dbOperations.get_monitoring_information_from_table(account_id)
            return monitoring_response
        except Exception as err:
            print("Error getting the monitoring information")
            return None

    async def modify_trip_status(self,account_id, trip_id,status):
        try:
            update_result = await self._dbOperations.alter_trip_status_in_table(account_id,trip_id,status)
            return update_result
        except Exception as err:
            print("Error starting the trip: ",err)
            return None
        
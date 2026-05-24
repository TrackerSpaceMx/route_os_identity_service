from database.operations_db import OperationsDB
import httpx


class VehichlesProcess:
    def __init__(self):
        self.__dbdOPerations = OperationsDB()
        self._events_all ="https://ws.fulltrack2.com/events/all/apiKey/"
    
    async def validate_fulltrack_keys(self,api_key,secret_key):
        try:
            url = f"{self._events_all}{api_key}/secretKey/{secret_key}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                status_code = response.status_code
                if status_code == 403:
                    return False
            return True
        except Exception as err:
            print("Error validating fulltrack keys: ",err)
            return False

    async def show_vehicles():
        try:
            pass
        except Exception as err:
            print("Error showing vehicles: ",err)
from database.operations_db import OperationsDB
import httpx


class VehichlesProcess:
    def __init__(self):
        self.__dbOPerations = OperationsDB()
        self._events_all ="https://ws.fulltrack2.com/events/all/apiKey/"
        self._vehicles_all ="https://ws.fulltrack2.com/vehicles/all/apiKey/"

    async def get_fulltrack_keys(self,account_id):
        try:
            api_key,secret_key= await self.__dbOPerations.get_keys_from_table(account_id)
            return api_key,secret_key
        except Exception as err:
            print("Error getting the fulltrack keys: ",err)
    
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

    async def show_vehicles(self,account_id):
        try:
            api_key,secret_key = await self.get_fulltrack_keys(account_id)
            if api_key and secret_key:
                url = f"{self._events_all}{api_key}/secretKey/{secret_key}"
                async with httpx.AsyncClient() as client:
                    response = await client.get(url)
                    status_code = response.status_code
                    if status_code == 200:
                        vehicles=[]
                        data = response.json()
                        data_content = data.get("data",None)
                        for vehicle in data_content:
                            driver= vehicle.get("ras_mot_nome",None)
                            plate = vehicle.get("ras_vei_placa")
                            if plate and plate!="":
                                if driver == "PADRAO":
                                    driver = "Sin conductor asignado"
                                vehicle_information = {"plate":plate,"driver":driver}
                                vehicles.append(vehicle_information)
                        if len(vehicle)>0:
                            return vehicles
                        else:
                            return "NO_CONTENT"
                    else:
                        return False
            else:
                return False
        except Exception as err:
            print("Error showing vehicles: ",err)
            return False
from database.operations_db import OperationsDB

class DriverProcess:
    def __init__(self):
        self._dbOperations = OperationsDB()

    

    async def create_driver(self,driver_information,account_id):
        try:
            driver_insertion_response =await  self._dbOperations.insert_driver_in_table(driver_information,account_id)
            return driver_insertion_response
        except Exception as err:
            print("Error inserting driver: ",err)
            return False
    
    async def show_drivers(self,account_id):
        try:
            drivers =await self._dbOperations.get_drivers_from_table(account_id)
            return drivers
        except Exception as err:
            print("Error getting drivers: ",err)
            return False
    
    async def remove_driver(self,driver_id, user_id, account_id):
        try:
            remove_response = await self._dbOperations.remove_driver_from_table(driver_id,user_id,account_id)
            return remove_response
        except Exception as err:
            print("Error removing driver: ",err)
            return False
    
    async def update_driver(self,account_id,driver_information,driver_id):
        try:
            update_driver_response = await self._dbOperations.update_driver_by_id(account_id,driver_information,driver_id)
            return update_driver_response
        except Exception as err:
            print("Error updating driver: ",err)
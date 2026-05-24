from database.operations_db import OperationsDB

class RoutesProcess:
    def __init__(self):
        self._dbOperations  = OperationsDB()


    async def create_point(self,point_information,account_id,user_id):
        try:
            point_insertion_results= await self._dbOperations.register_point_in_table(point_information,account_id,user_id)
            return point_insertion_results
        except Exception as err:
            print("Error inserting the point: ",err)
            return False
    
    async def get_points(self,account_id):
        try:
            points = await self._dbOperations.get_points_from_table(account_id) 
            return points
        except Exception as err:
            print("Error getting the points: ",err)
            return False
    
    async def remove_point(self,point_id,user_id,account_id):
        try:
            elimination_result = await self._dbOperations.remove_point_for_table(point_id,user_id,account_id)
            return elimination_result
        except Exception as err:
            print("Error deleting point: ",err)
            return False

    async def create_route(self,route_body,account_id,user_id):
        try:
            print("here to create route: ",route_body)
            route_creation_response = await self._dbOperations.create_route_in_table(route_body,account_id,user_id)
            return route_creation_response
        except Exception as err:
            print("Error creating the route: ",err)

    
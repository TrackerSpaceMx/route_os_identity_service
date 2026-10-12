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
            route_creation_response = await self._dbOperations.create_route_in_table(route_body,account_id,user_id)
            return route_creation_response
        except Exception as err:
            print("Error creating the route: ",err)

    async def get_routes(self,account_id):
        try:
            routes = await self._dbOperations.get_routes_from_table(account_id)
            return routes
        except Exception as err:
            print("Error getting the routes: ",err)
            return None


    async def get_waypoints_from_route(self,route_id):
        try:
            waypoints_response = await self._dbOperations.get_waypoints_from_table(route_id)
            return waypoints_response
        except Exception as err:
            print("Error getting the waypoints from route:" ,err,route_id)
            return None

    async def delete_route_from_table(self,account_id,route_id):
        try:
            route_deletion_response = await self._dbOperations.remove_route_from_table(account_id,route_id)
            return route_deletion_response
        except Exception as err:
            print("Error deleting route:",err)
            return None


    async def create_trip(self,account_id,user_id,trip_information):
        try:
            trip_creation_response = await self._dbOperations.insert_trip_in_tables(account_id,user_id,trip_information)
            print("RESPONSE : ",trip_creation_response)
            return trip_creation_response
        except Exception as err:
            print("Error creating trip: ",err)


    async def show_trips(self,account_id):
        try:
            trips = await self._dbOperations.get_trips_from_table(account_id)
            return trips
        except Exception as err:
            print("Error getting the trips from table: ",err)

    async def remove_trip(self,account_id,trip_id):
        try:
            remove_result = await self._dbOperations.remove_trip_from_table(account_id,trip_id)
            return remove_result
        except Exception as err:
            print("Error removing trip: ",err)
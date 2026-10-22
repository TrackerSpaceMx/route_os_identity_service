from database.mysql_operations import MysqlOperations
import bcrypt
from datetime import timedelta
import json
import uuid

class OperationsDB:
    def __init__(self):
        self.__mysqlOperations = MysqlOperations()

    @staticmethod
    def mexico_to_utc(dt):
        if dt is None:
            return None
        return dt - timedelta(hours=6)  

    def validate_password(self, password_input,password_hash):
        password_input_encoded = password_input.encode("utf-8")
        password_hash_encoded = password_hash.encode("utf-8")
        if bcrypt.checkpw(password_input_encoded,password_hash_encoded):
            return True
        else:
            return False

    async def get_account(self,slug:str):
        return await self.__mysqlOperations.select_accounts(slug)

    async def insert_user_in_table(self, account_id,user_information,password_hash,is_owner=0):
        uuid_account= account_id
        if not uuid_account:
            return False
        return await self.__mysqlOperations.insert_user(user_information,uuid_account,password_hash,is_owner)
        

    async def validate_user_from_table(self,user_information,slug):
        result= False
        username = user_information.get("username",None)
        password_input = user_information.get("password",None)
        if username:
            user_information_db = await self.__mysqlOperations.select_user(username,slug)
            if user_information and len(user_information_db)>0:
                username_db= user_information_db[0][0]
                password_hash =  user_information_db[0][1]
                password_validation = self.validate_password(password_input,password_hash)
                user_id = user_information_db[0][2]
                role = user_information_db[0][3]
                if password_validation:
                    result_dictionary = {"user":username_db,"id":user_id,"role": role}
                    result = result_dictionary
        return result
    

    async def validate_user_from_table_account(self,user_information):
        result= False
        username = user_information.get("username",None)
        password_input = user_information.get("password",None)
        if username:
            user_information_db = await self.__mysqlOperations.select_user_account(username)
            if user_information and len(user_information_db)>0:
                
                username_db= user_information_db[0][0]
                password_hash =  user_information_db[0][1]
                password_validation = self.validate_password(password_input,password_hash)
                user_id = user_information_db[0][2]
                if password_validation:
                    result_dictionary = {"user":username_db,"id":user_id}
                    result = result_dictionary
        return result
        
    
    async def update_user(self,account: str, body:dict,user_to_update:str):
        result = False
        update_result = await self.__mysqlOperations.update_user(account, body,user_to_update)
        if update_result:
            result = update_result
        return result
    

    async def delete_user_from_database(self, account:str, username:str):
        owner_validation = await self.__mysqlOperations.select_owner_status(username,account)
        if owner_validation:
            owner_status= owner_validation[0][0]
            if owner_status ==1:
                return "FORBIDDEN"
            return await self.__mysqlOperations.delete_user(account,username)
        return False

    async def query_user_by_email(self, email,account_id):
        user_response = await self.__mysqlOperations.select_user_email(email,account_id)
        if user_response and len(user_response)>0:
            return user_response
        return False
    
    async def save_token_to_reset_password(self,user_id,token,purpose):
        return await self.__mysqlOperations.insert_token(user_id,token,purpose)


    async def get_token_data(self,token):
        token_data= await self.__mysqlOperations.select_token(token)
        if token_data:
            user_id = token_data[1]
            return {"user_id":user_id}
        return False

    async def update_new_password_and_set_token_as_used(self,user_id:str,new_password:str,account:str,token:str):
        update_password_response = await self.__mysqlOperations.update_password(user_id,new_password,account)
        if update_password_response:
            print("Password updated")
            token_status= await self.__mysqlOperations.token_status(token)
            if token_status:
                return True
        return False


    async def select_account_user_by_id_and_username(self, user_id,username):
        user_response = await self.__mysqlOperations.select_user_account_with_id(username,user_id)
        return user_response
    
    async def register_account_in_table(self,account):
        account_result = await self.__mysqlOperations.insert_account(account)
        return account_result


    async def delete_account_from_table_with_users(self,slug_account):
        delete_response = await self.__mysqlOperations.delete_account(slug_account)
        return delete_response
    

    async def get_accounts_from_table(self):
        accounts_response = await self.__mysqlOperations.select_all_accounts()
        if accounts_response is None:
            return "NO_CONTENT"
        if accounts_response:
            accounts = []
            for account in accounts_response:
                account_dictionary = {"id":account[0],"slug":account[1],"name":account[2],"company":account[3],"rfc":account[4],"created_at":account[5]}
                accounts.append(account_dictionary)
            return accounts
        else:
            return False
    
    async def get_account_by_id(self,display_id):
        account_information = await self.__mysqlOperations.select_account_by_id(display_id)
        account_id = account_information[0][0]
        return account_id

    
    async def get_users_from_account(self,account_id):
        users_response = await self.__mysqlOperations.select_users(account_id)
        users =[]
        if users_response:
            for user in users_response:
                is_owner = user[8]
                print
                users_information= {"username":user[0],"role":user[1],"created_at":user[2],"email":user[3],"status":user[4],"phone":user[5],"recovery_email":user[6],"last_login_at":user[7],"name":user[9],"user_id":user[10]}
                if is_owner == 1:
                    users_information.update({"clientes_information":"all"})
                else:
                    clients_information = json.loads(user[11])
                    users_information.update({"clientes_information":clients_information})
                users.append(users_information)
            if len(users)>0:
                return users
        return False
    

    async def register_point_in_table(self,point_information,account_id,user_id):
        return await self.__mysqlOperations.insert_point(point_information,account_id,user_id)


    async def get_points_from_table(self,account_id):
        
        points_result = await self.__mysqlOperations.select_points(account_id) 
        points =[]
        if points_result:
            for point in points_result:
                point_information ={
                    "id":point[0],
                    "point_id":point[1],
                    "created_by":point[8],
                    "point_name":  point[3],
                    "category": point[4],
                    "coordinates": [point[5],point[6]],
                    "radius": point[9],
                    "created_at": point[7]
                }
                points.append(point_information)
            return points
        else:
            return "NO_CONTENT"

    async def remove_point_for_table(self,point_id,user_id,account_id):
        return await self.__mysqlOperations.delete_point(point_id,user_id,account_id)


    async def create_route_in_table(self,route_body,account_id,user_id):
        points = route_body.get("points",[])
        route_response = await self.__mysqlOperations.insert_route(route_body,account_id,user_id)
        waypoints_of_the_route=[]
        if route_response  == "DUPLICATE":
            return "DUPLICATE"

        elif route_response:
            route_id = await self.__mysqlOperations.select_route_by_display_id(route_response)
            if route_id and len(route_id)>0:
                route_id_mysql = route_id[0][0]
                for waypoint in points:
                    value_mysql =(route_id_mysql,waypoint["point_id"],waypoint["id"],waypoint["point_name"])
                    waypoints_of_the_route.append(value_mysql)
                
                waypoints_response = await self.__mysqlOperations.insert_waypoints(waypoints_of_the_route)
                return waypoints_of_the_route
            else:
                return False

        else:
            return False
        
    

    
    async def get_keys_from_table(self,account_id):
        keys_response = await self.__mysqlOperations.select_keys(account_id)
        if keys_response and len(keys_response)>0:
            api_key = keys_response[0][0]
            secret_key = keys_response[0][1]
            return api_key,secret_key
        else:
            return False,False
    

    async def insert_driver_in_table(self,driver_information,account_id):
        return await self.__mysqlOperations.insert_driver(driver_information,account_id)
    

    async def get_drivers_from_table(self,account_id):
        drivers_response = await self.__mysqlOperations.select_drivers(account_id)
        print("select drivers: ",drivers_response)
        drivers=[]
        if drivers_response and len(drivers_response)>0:
            for driver in drivers_response:
                driver_structure= {"id":driver[0],"display_id":driver[1],"name":driver[2],"employee_number":driver[3],"phone":driver[4],"phone_secondary":driver[5],"photo_url":driver[6],"license_number" : driver[7], "license_expiry": driver[8],"available": True if driver[9] == 0 else False,"notes":driver[10]}
                drivers.append(driver_structure)
            return drivers
        else:
            return "NO_CONTENT"
    

    async def remove_driver_from_table(self,driver_id, user_id, account_id):
        remove_driver_response = await self.__mysqlOperations.delete_driver(driver_id,user_id,account_id)        
        return remove_driver_response
    
    async def update_driver_by_id(self,account_id,driver_information,driver_id):
        driver_response = await self.__mysqlOperations.update_driver(account_id,driver_information,driver_id)
        return driver_response

    async def get_routes_from_table(self,account_id):
        routes_response = await self.__mysqlOperations.select_routes(account_id)
        routes =[]
        if routes_response:
            for route in routes_response:
                route_structure = {"route_id":route[0],"route_name":route[1],"creation_date":route[2],"created_by":route[3]}
                routes.append(route_structure)
            return routes
        else:
            return "NO_CONTENT"


    async def get_waypoints_from_table(self,route_id):
            waypoints_response = await self.__mysqlOperations.select_waypoints(route_id)
            waypoints =[]
            if waypoints_response:
                for waypoint in waypoints_response:
                    waypoint_structure = {"waypoint_id":waypoint[0],"route_id":waypoint[1],"waypoint_order":waypoint[2],"waypoint_label":waypoint[3]}
                    waypoints.append(waypoint_structure)
                return waypoints
            else:
                return "NO_CONTENT"


    async def remove_route_from_table(self, account_id,route_id):
            remove_route_response = await self.__mysqlOperations.delete_route(account_id,route_id)
            return remove_route_response

    async def insert_trip_in_tables(self,account_id,user_id,trip_information):
        driver_id = trip_information.get("driver_id")
        driver_validation = await self.__mysqlOperations.select_driver_status(account_id,driver_id)
        driver_status = driver_validation[0][0]
        if driver_status ==1:
            return "DRIVER_IN_ROUTE"
        waypoints = trip_information.get("stops")
        for wp in waypoints:
            wp["expected_arrival"] = OperationsDB.mexico_to_utc(wp.get("expected_arrival"))
        trip_insertion = await self.__mysqlOperations.insert_trip(account_id,user_id,trip_information,waypoints)
        created_status = trip_insertion.get("created")

        if created_status:
            driver_update_status = await self.__mysqlOperations.update_driver_status(account_id,1,driver_id)
            return True
        else:
            return False



    async def get_trips_from_table(self,account_id):
        trips_response = await self.__mysqlOperations.select_trips(account_id)
        trips =[]
        if trips_response:
            for trip in trips_response:
                trip_structure = {"trip_id":trip[0],"display_id":trip[1],"vehicle":trip[2],"status":trip[3],"created_at":trip[4],"route":trip[5],"driver":trip[6],"created_by":trip[7]}
                trips.append(trip_structure)
            return trips
        else:
            return "NO_CONTENT"


    async def remove_trip_from_table(self,account_id,trip_id):
        remove_trip_response = await self.__mysqlOperations.delete_trip_assignment(account_id,trip_id)
        if remove_trip_response:            
            release_driver = await self.__mysqlOperations.update_driver_status(account_id,0,remove_trip_response)
        return remove_trip_response

    async def update_last_login_in_table(self,user_id,account_id):
        update_last_login = await self.__mysqlOperations.update_last_login(user_id,account_id)
        return update_last_login

    async def get_user_by_display_id(self,display_id,account_id,username):
        user_id_response = await self.__mysqlOperations.select_user_by_display_id(display_id,account_id,username)
        if user_id_response and len(user_id_response)>0:
            user_uuid = user_id_response[0][1]
            return user_uuid
        return None

    async def get_s3_url_from_driver(self,account_id,driver_id):
        url_response = await self.__mysqlOperations.select_driver_photo_key(account_id,driver_id)
        if not url_response:
            return False
        
        url_s3 = url_response[0][0]

        return url_s3


    async def create_protocol_profile(self, account_id, user_id, data: dict, rule_defs: dict, locked_rules: set):
        profile_id = str(uuid.uuid4())
        rule_rows, action_rows = [], []

        for r in data["rules"]:
            rule_id = str(uuid.uuid4())
            rule_rows.append((
                rule_id, profile_id, r["rule_type"],
                rule_defs[r["rule_type"]]["category"],
                int(r["is_enabled"]),
                int(r["rule_type"] in locked_rules),
                r["severity"], r["risk_impact"],
                r.get("threshold_value"), r.get("threshold_unit"),
                json.dumps(r["params"]) if r.get("params") else None,
            ))
            for i, a in enumerate(r.get("actions", [])):
                action_rows.append((
                    str(uuid.uuid4()), rule_id, a["action_type"],
                    a["delay_minutes"], int(a["escalate"]), i,
                    json.dumps(a["config"]) if a.get("config") else None,
                ))

        return await self.__mysqlOperations.create_protocol_profile_mysql(
            profile_id, account_id, user_id, data, rule_rows, action_rows
        )

    async def get_protocol_profiles_from_table(self, account_id):
        response = await self.__mysqlOperations.select_protocol_profiles(account_id)
        profiles = []
        if response:
            for p in response:
                profiles.append({
                    "id": p[0], "display_id": p[1], "name": p[2],
                    "description": p[3], "is_default": bool(p[4]),
                    "created_at": p[5], "created_by": p[6], "active_rules": p[7],
                })
            return profiles
        return "NO_CONTENT"
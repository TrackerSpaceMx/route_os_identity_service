import asyncmy
import asyncio
import json
import traceback
from asyncmy.pool import Pool
from asyncmy.errors import IntegrityError
from control.configuration import Config

QUERY_TIMEOUT = 10.0  


class MysqlOperations:
    _pool: Pool = None
    _lock = asyncio.Lock()

    @classmethod
    async def _get_pool(cls) -> Pool:
        if cls._pool is None:
            async with cls._lock:
                if cls._pool is None:
                    cls._pool = await asyncmy.create_pool(
                        host=Config.DB_HOST,
                        db=Config.DB_NAME,
                        user=Config.DB_USER,
                        password=Config.DB_PASSWORD,
                        charset="utf8mb4",
                        maxsize=15,
                        minsize=3,
                        pool_recycle=1800,
                        autocommit=True,      
                        connect_timeout=10, 
                    )
        return cls._pool

    async def pool_status(self):
        pool = await self._get_pool()
        print(f"Free: {pool.freesize} | Used: {pool.size - pool.freesize} | Max: {pool.maxsize}")

    async def _fetch(self, query: str, params: tuple = (), one: bool = False):
        """SELECT genérico. Retorna tuple de filas, o una sola fila si one=True."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await asyncio.wait_for(cur.execute(query, params), timeout=QUERY_TIMEOUT)
                result = await cur.fetchone() if one else await cur.fetchall()
                if not one:
                    return result if result else ()
                return result 

    async def _execute(self, query: str, params: tuple = ()):
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await asyncio.wait_for(cur.execute(query, params), timeout=QUERY_TIMEOUT)
                if cur.lastrowid:
                    return cur.lastrowid
                return cur.rowcount > 0

    async def _execute_many(self, query: str, params: list) -> bool:
        """INSERT múltiple."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await asyncio.wait_for(cur.executemany(query, params), timeout=QUERY_TIMEOUT)
                return cur.rowcount > 0


    async def select_accounts(self, slug_account: str) -> tuple:
        try:
            return await self._fetch(
                "SELECT * FROM accounts WHERE slug = %s", (slug_account,)
            )
        except Exception as err:
            print("Error selecting accounts:", err)
            return ()

    async def select_account_by_id(self, display_id: int) -> tuple:
        try:
            return await self._fetch(
                "SELECT * FROM accounts WHERE display_id = %s", (display_id,)
            )
        except Exception as err:
            print("Error selecting account by id:", err)
            return ()

    async def select_all_accounts(self) -> tuple:
        try:
            return await self._fetch(
                "SELECT display_id,slug,name,company_name,rfc,created_at FROM accounts"
            )
        except Exception as err:
            print("Error selecting all accounts:", err)
            return ()

    async def select_keys(self, account_id) -> tuple:
        try:
            return await self._fetch(
                "SELECT api_key_hash,secret_key_hash FROM accounts WHERE id=%s", (account_id,)
            )
        except Exception as err:
            print("Error selecting keys:", err)
            return ()

    async def insert_account(self, account: dict):
        try:
            return await self._execute(
                """INSERT INTO accounts(slug,name,api_key_hash,secret_key_hash,rfc,address,company_name)
                   VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                (account["slug"], account["name"], account["api_key"],
                 account["secret_key"], account["rfc"], account["address"], account["company_name"])
            )
        except IntegrityError as err:
            return "DUPLICATE" if err.args[0] == 1062 else False
        except Exception as err:
            print("Error inserting account:", err)
            return False

    async def delete_account(self, slug_account: str) -> bool:
        try:
            return await self._execute(
                "DELETE FROM accounts WHERE slug = %s", (slug_account,)
            )
        except Exception as err:
            print("Error deleting account:", err)
            return False


    async def select_user(self, user: str, account: str) -> tuple:
        try:
            return await self._fetch(
                "SELECT username,password_hash,id,role FROM route_os_users WHERE username=%s AND account_id=%s",
                (user, account)
            )
        except Exception as err:
            print("Error selecting user:", err)
            return ()

    async def select_user_email(self, email: str, account: str) -> tuple:
        try:
            return await self._fetch(
                "SELECT username,password_hash,id,role FROM route_os_users WHERE email=%s AND account_id=%s",
                (email, account)
            )
        except Exception as err:
            print("Error selecting user by email:", err)
            return ()

    async def select_owner_status(self, user: str, account: str) -> tuple:
        try:
            return await self._fetch(
                "SELECT is_owner FROM route_os_users WHERE username=%s AND account_id=%s",
                (user, account)
            )
        except Exception as err:
            print("Error selecting owner status:", err)
            return ()

    async def select_users(self, account_id) -> tuple:
        try:
            return await self._fetch(
                "SELECT username,role,created_at,email,status,phone,recovery_email FROM route_os_users WHERE account_id=%s",
                (account_id,)
            )
        except Exception as err:
            print("Error selecting users:", err)
            return ()

    async def select_user_account(self, user: str) -> tuple:
        try:
            return await self._fetch(
                "SELECT username,password_hash,id FROM route_os_users_auth WHERE username=%s",
                (user,)
            )
        except Exception as err:
            print("Error selecting user account:", err)
            return ()

    async def select_user_account_with_id(self, user: str, user_id: str) -> tuple:
        try:
            return await self._fetch(
                "SELECT username,password_hash,id FROM route_os_users_auth WHERE username=%s AND id=%s",
                (user, user_id)
            )
        except Exception as err:
            print("Error selecting user account with id:", err)
            return ()

    async def insert_user(self, user_information: dict, account_uuid: str, password_hash: str, owner: int = 0):
        try:
            return await self._execute(
                """INSERT INTO route_os_users
                   (account_id,name,username,email,phone,password_hash,recovery_email,role,is_owner)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (account_uuid, user_information["name"], user_information["username"],
                 user_information["email"], user_information["phone"], password_hash,
                 user_information["recovery_email"], user_information["role"], owner)
            )
        except IntegrityError as err:
            return "DUPLICATE" if err.args[0] == 1062 else False
        except Exception as err:
            print("Error inserting user:", err)
            return False

    async def update_user(self, account: str, body: dict, user_to_update: str):
        try:
            fields = [f"{key} = %s" for key in body]
            values = (*body.values(), account, user_to_update)
            return await self._execute(
                f"UPDATE route_os_users SET {', '.join(fields)} WHERE account_id=%s AND username=%s",
                values
            )
        except IntegrityError as err:
            return "DUPLICATE" if err.args[0] == 1062 else False
        except Exception as err:
            print("Error updating user:", err)
            return False

    async def delete_user(self, account: str, username: str) -> bool:
        try:
            return await self._execute(
                "DELETE FROM route_os_users WHERE account_id=%s AND username=%s AND is_owner=0",
                (account, username)
            )
        except Exception as err:
            print("Error deleting user:", err)
            return False

    async def update_password(self, user_id: str, new_password: str, account: str) -> bool:
        try:
            return await self._execute(
                "UPDATE route_os_users SET password_hash=%s WHERE account_id=%s AND id=%s",
                (new_password, account, user_id)
            )
        except Exception as err:
            print("Error updating password:", err)
            traceback.print_exc()
            return False

    async def insert_token(self, user_id: str, token: str) -> bool:
        try:
            return await self._execute(
                """INSERT INTO route_os_password_resets(user_id,token,expires_at)
                   VALUES(%s,%s,NOW() + INTERVAL 1 HOUR)""",
                (user_id, token)
            )
        except Exception as err:
            print("Error saving recovery token:", err)
            return False

    async def select_token(self, token: str):
        """Retorna una fila o None."""
        try:
            return await self._fetch(
                "SELECT * FROM route_os_password_resets WHERE token=%s AND used=%s AND expires_at > NOW()",
                (token, 0),
                one=True
            )
        except Exception as err:
            print("Error selecting token:", err)
            return None

    async def token_status(self, token: str) -> bool:
        try:
            return await self._execute(
                "UPDATE route_os_password_resets SET used=%s WHERE token=%s",
                (1, token)
            )
        except Exception as err:
            print("Error updating token status:", err)
            traceback.print_exc()
            return False

    async def insert_point(self, point_information: dict, account_uuid: str, user_id: str):
        try:
            return await self._execute(
                """INSERT INTO points_of_interest
                   (account_id,user_id,point_name,category,latitude,longitude,radius_meters)
                   VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                (account_uuid, user_id, point_information["point_name"],
                 point_information["category"], point_information["latidude"],
                 point_information["longitude"], point_information["radius_meter"])
            )
        except IntegrityError as err:
            return "DUPLICATE" if err.args[0] == 1062 else False
        except Exception as err:
            print("Error inserting point:", err)
            return False

    async def select_points(self, account_id) -> tuple:
        try:
            return await self._fetch(
                """SELECT point.display_id, point.id, point.user_id, point.point_name,
                          point.category, point.latitude, point.longitude, point.created_at,
                          user.username AS created_by_name, point.radius_meters
                   FROM points_of_interest point
                   INNER JOIN route_os_users user ON user.id = point.user_id
                   WHERE point.account_id = %s""",
                (account_id,)
            )
        except Exception as err:
            print("Error selecting points:", err)
            return ()

    async def delete_point(self, point_id, user_id, account_id) -> bool:
        try:
            return await self._execute(
                "DELETE FROM points_of_interest WHERE display_id=%s AND user_id=%s AND account_id=%s",
                (point_id, user_id, account_id)
            )
        except Exception as err:
            print("Error deleting point:", err)
            return False


    async def insert_route(self, route_body: dict, account_id: str, user_id: str):
        try:
            return await self._execute(
                """INSERT INTO routeos_os_routes(account_id,created_by,route_name,active_days)
                   VALUES(%s,%s,%s,%s)""",
                (account_id,
                 user_id, route_body["route_name"], json.dumps(route_body["active_days"]))
            )
        except IntegrityError as err:
            return "DUPLICATE" if err.args[0] == 1062 else False
        except Exception as err:
            print("Error inserting route:", err)
            return False

    async def insert_waypoints(self, waypoints: list) -> bool:
        try:
            return await self._execute_many(
                """INSERT INTO route_os_waypoints(route_id,poi_id,sequence_order,label,dwell_time)
                   VALUES(%s,%s,%s,%s,%s)""",
                waypoints
            )
        except Exception as err:
            print("Error inserting waypoints:", err)
            return False

    async def select_route_by_display_id(self, display_id) -> tuple:
        try:
            return await self._fetch(
                "SELECT id FROM routeos_os_routes WHERE display_id=%s", (display_id,)
            )
        except Exception as err:
            print("Error selecting route:", err)
            return ()



    async def insert_driver(self, driver: dict, account_id: str):
        try:
            return await self._execute(
                """INSERT INTO drivers(account_id,name,sex,phone,address)
                   VALUES(%s,%s,%s,%s,%s)""",
                (account_id, driver["name"], driver["sex"], driver["phone"], driver["address"])
            )
        except IntegrityError as err:
            return "DUPLICATE" if err.args[0] == 1062 else False
        except Exception as err:
            print("Error inserting driver:", err)
            return False

    async def select_drivers(self, account_id) -> tuple:
        try:
            return await self._fetch(
                "SELECT display_id,name,sex,phone,address FROM drivers WHERE account_id=%s",
                (account_id,)
            )
        except Exception as err:
            print("Error selecting drivers:", err)
            return ()
    

    async def delete_driver(self, driver_id, user_id, account_id) -> bool:
        try:
            return await self._execute(
                "DELETE FROM drivers WHERE display_id=%s  AND account_id=%s",
                (driver_id, account_id)
            )
        except Exception as err:
            print("Error deleting driver:", err)
            return False
    

    async def update_driver(self, account: str, body: dict, driver_to_update: str):
        try:
            fields = [f"{key} = %s" for key in body]
            values = (*body.values(), account, driver_to_update)
            return await self._execute(
                f"UPDATE drivers SET {', '.join(fields)} WHERE account_id=%s AND display_id=%s",
                values
            )
        except IntegrityError as err:
            return "DUPLICATE" if err.args[0] == 1062 else False
        except Exception as err:
            print("Error updating user:", err)
            return False


    async def select_routes(self, account_id) -> tuple:
        try:
            return await self._fetch(
                """
                SELECT r.id, r.route_name, r.created_at, u.username
                FROM routeos_os_routes r
                JOIN route_os_users u ON r.created_by = u.id
                WHERE r.account_id = %s
                """,
                (account_id,)
            )
        except Exception as err:
            print("Error selecting the routes:", err)
            return ()


    
    async def select_waypoints(self, route_id) -> tuple:
        try:
            return await self._fetch(
                            "SELECT id,route_id,sequence_order,label FROM route_os_waypoints WHERE route_id=%s ",
                            (route_id,)
                        )
        except Exception as err:
            print("Error selecting the routes:", err)
            return ()


    async def delete_route(self, account_id,route_id) -> bool:
            try:
                return await self._execute(
                    "DELETE FROM routeos_os_routes WHERE account_id=%s  AND id=%s",
                    (account_id,route_id)
                )
            except Exception as err:
                print("Error deleting driver:", err)
                return False
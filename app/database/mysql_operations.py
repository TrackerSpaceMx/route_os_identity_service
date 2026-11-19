import asyncmy
import asyncio
import json
import traceback
from asyncmy.pool import Pool
from asyncmy.errors import IntegrityError
from control.configuration import Config
import uuid
import hashlib
from contextlib import asynccontextmanager

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

    @asynccontextmanager
    async def transaction(self):
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.begin()
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

    async def pool_status(self):
        pool = await self._get_pool()
        print(f"Free: {pool.freesize} | Used: {pool.size - pool.freesize} | Max: {pool.maxsize}")

    async def _fetch(self, query: str, params: tuple = (), one: bool = False):
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

    async def select_user_by_display_id(self, display_id: str, account: str,username:str) -> tuple:
        try:
            return await self._fetch(
                "SELECT username,id,role FROM route_os_users WHERE display_id=%s AND account_id=%s AND username =%s",
                (display_id, account,username)
            )
        except Exception as err:
            print("Error selecting user:", err)
            return ()

    async def select_user_email(self, email: str, account: str) -> tuple:
        try:
            return await self._fetch(
                "SELECT username,password_hash,id,role FROM route_os_users WHERE recovery_email=%s AND account_id=%s",
                (email, account)
            )
        except Exception as err:
            print("Error selecting user by email:", err)
            return ()

    async def select_owner_status(self, user: str, account: str) -> tuple:
        try:
            return await self._fetch(
                "SELECT is_owner FROM route_os_users WHERE id=%s AND account_id=%s",
                (user, account)
            )
        except Exception as err:
            print("Error selecting owner status:", err)
            return ()

    async def select_users(self, account_id) -> tuple:
        try:
            return await self._fetch(
                """
                SELECT 
                    u.username,
                    u.role,
                    u.created_at,
                    u.email,
                    u.status,
                    u.phone,
                    u.recovery_email,
                    u.last_login,
                    u.is_owner,
                    u.name,
                    u.id,
                    JSON_ARRAYAGG(
                        JSON_OBJECT(
                            'client_id', ca.client_id,
                            'client_name', ca.client_name
                        )
                    ) AS clients
                FROM route_os_users u
                LEFT JOIN clients_assigned ca 
                    ON ca.user_id = u.id 
                    AND ca.account_id = u.account_id
                WHERE u.account_id = %s
                GROUP BY u.id
                """,
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

    async def insert_user(self, user_information: dict, account_uuid: str,
                          password_hash: str, owner: int = 0):
        try:
            user_id = str(uuid.uuid4())

            clients = {}
            for c in user_information.get("clients_information") or []:
                clients[int(c["client_id"])] = str(c["client_name"]).strip()[:255]

            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.begin()  
                try:
                    async with conn.cursor() as cur:
                        await asyncio.wait_for(
                            cur.execute(
                                """INSERT INTO route_os_users
                                   (id, account_id, name, username, email, phone,
                                    password_hash, recovery_email, role, is_owner)
                                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                (user_id, account_uuid, user_information["name"],
                                 user_information["username"], user_information["email"],
                                 user_information["phone"], password_hash,
                                 user_information["recovery_email"],
                                 user_information["role"], owner)
                            ),
                            timeout=QUERY_TIMEOUT
                        )
                        display_id = cur.lastrowid  

                        if clients:
                            await asyncio.wait_for(
                                cur.executemany(
                                    """INSERT INTO clients_assigned
                                       (user_id, account_id, client_id, client_name)
                                       VALUES (%s,%s,%s,%s)""",
                                    [(user_id, account_uuid, cid, name)
                                     for cid, name in clients.items()]
                                ),
                                timeout=QUERY_TIMEOUT
                            )
                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise

            return display_id
        except IntegrityError as err:
            return "DUPLICATE" if err.args[0] == 1062 else False
        except (KeyError, ValueError, TypeError) as err:
            print("Invalid user data:", err)
            return False
        except Exception as err:
            print("Error inserting user:", err)
            return False

    async def update_user(self, account: str, body: dict, user_to_update: str):
        try:
            clients = body.pop("clients_information", None)

            row = await self._fetch(
                "SELECT id FROM route_os_users WHERE account_id=%s AND id=%s",
                (account, user_to_update),
                one=True
            )
            if not row:
                return False
            user_id = row[0]

            if body:
                fields = [f"{key} = %s" for key in body]
                values = (*body.values(), account, user_to_update)
                await self._execute(
                    f"UPDATE route_os_users SET {', '.join(fields)} WHERE account_id=%s AND id=%s",
                    values
                )

            if clients is not None:
                await self._execute(
                    "DELETE FROM clients_assigned WHERE user_id=%s AND account_id=%s",
                    (user_id, account)
                )
                if clients:
                    await self._execute_many(
                        "INSERT INTO clients_assigned (user_id, account_id, client_id, client_name) VALUES (%s, %s, %s, %s)",
                        [(user_id, account, c["client_id"], c["client_name"]) for c in clients]
                    )

            return True

        except IntegrityError as err:
            return "DUPLICATE" if err.args[0] == 1062 else False
        except Exception as err:
            print("Error updating user:", err)
            return False

    async def delete_user(self, account: str, username: str) -> bool:
        try:
            return await self._execute(
                "DELETE FROM route_os_users WHERE account_id=%s AND id=%s AND is_owner=0",
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

    async def update_last_login(self, user_id: str, account: str) -> bool:
        try:
            return await self._execute(
                "UPDATE route_os_users SET last_login=CURRENT_TIMESTAMP WHERE account_id=%s AND id=%s",
                ( account, user_id)
            )
        except Exception as err:
            print("Error updating last login :", err)
            traceback.print_exc()
            return False

    async def insert_token(self, user_id: str, token: str, purpose) -> bool:

        hours = {"reset": 1, "invite": 24}
        if purpose not in hours:
            raise ValueError(f"purpose inválido: {purpose}")

        token_hash = hashlib.sha256(token.encode()).hexdigest()

        try:
            await self._execute(
                """UPDATE route_os_password_resets
                SET used_at = UTC_TIMESTAMP()
                WHERE user_id = %s AND purpose = %s AND used_at IS NULL""",
                (user_id, purpose)
            )

            return await self._execute(
                """INSERT INTO route_os_password_resets (user_id, purpose, token, expires_at)
                VALUES (%s, %s, %s, UTC_TIMESTAMP() + INTERVAL %s HOUR)""",
                (user_id, purpose, token_hash, hours[purpose])
            )
        except Exception as err:
            print("Error saving token:", err)
            return False

    async def select_token(self, token: str):
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            return await self._fetch(
                """SELECT * FROM route_os_password_resets
                WHERE token = %s
                    AND purpose IN ('reset', 'invite')
                    AND used_at IS NULL
                    AND expires_at > UTC_TIMESTAMP()
                    AND failed_attempts < 5""",
                (token_hash,),
                one=True
            )
        except Exception as err:
            print("Error selecting token:", err)
            return None

    async def token_status(self, token: str) -> bool:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            return await self._execute(
                """UPDATE route_os_password_resets
                SET used_at = UTC_TIMESTAMP()
                WHERE token = %s
                    AND used_at IS NULL
                    AND expires_at > UTC_TIMESTAMP()""",
                (token_hash,)
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


    async def get_first_route_using_point(self, point_id):
            try:
                return await self._fetch(
                    """
                    SELECT r.id, r.display_id, r.route_name, w.sequence_order
                    FROM route_os_waypoints w
                    JOIN routeos_os_routes r ON r.id = w.route_id
                    WHERE w.poi_id = %s AND r.deleted_at IS NULL
                    ORDER BY r.created_at ASC
                    LIMIT 1
                    """,
                    (point_id,),
                    one=True
                )
            except Exception as err:
                print("Error checking point usage:", err)
                return None

    async def delete_point(self, point_id, user_id, account_id) -> dict:
        try:
            blocking_route = await self.get_first_route_using_point(point_id)
            print("ACCOUNT ID: ",account_id)
            print("USER ID: ",user_id)
            print("BLOCKING RESPONSE: ",blocking_route)

            if blocking_route:
                return {
                    "deleted": False,
                    "reason": "point_in_use",
                    "route_id": blocking_route[0],
                    "route_display_id": blocking_route[1],
                    "route_name": blocking_route[2]
                }
            print("HERE IN DELTE")
            success = await self._execute(
                "DELETE FROM points_of_interest WHERE id=%s  AND account_id=%s",
                (point_id, account_id)
            )
            return {"deleted": bool(success), "reason": None}

        except Exception as err:
            print("Error deleting point:", err)
            return {"deleted": False, "reason": "error"}


    async def insert_route(self, route_body: dict, account_id: str, user_id: str):
        try:
            return await self._execute(
                """INSERT INTO routeos_os_routes(account_id,created_by,route_name,client_name,client_id,starting_location)
                   VALUES(%s,%s,%s,%s,%s,%s)""",
                (account_id,
                 user_id, route_body["route_name"],route_body["client_name"],route_body["client_id"],route_body["starting_location"])
            )
        except IntegrityError as err:
            return "DUPLICATE" if err.args[0] == 1062 else False
        except Exception as err:
            print("Error inserting route:", err)
            return False

    async def insert_waypoints(self, waypoints: list) -> bool:
        try:
            return await self._execute_many(
                """INSERT INTO route_os_waypoints(route_id,poi_id,sequence_order,label)
                   VALUES(%s,%s,%s,%s)""",
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
                """INSERT INTO drivers(account_id,name,employee_number,phone,phone_secondary,photo_url,license_number,license_expiry,in_route)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (account_id, driver["name"], driver["employee_number"], driver["phone"], driver["phone_secondary"],driver["photo_url"],driver["license_number"],driver["license_expiry"],0)
            )
        except IntegrityError as err:
            return "DUPLICATE" if err.args[0] == 1062 else False
        except Exception as err:
            print("Error inserting driver:", err)
            return False

    async def select_drivers(self, account_id) -> tuple:
        try:
            return await self._fetch(
                "SELECT id,display_id,name,employee_number,phone,phone_secondary,photo_url,license_number,license_expiry,in_route,notes FROM drivers WHERE account_id=%s",
                (account_id,)
            )
        except Exception as err:
            print("Error selecting drivers:", err)
            return ()

    async def select_driver_status(self, account_id,driver_id) -> tuple:
            try:
                return await self._fetch(
                    "SELECT in_route FROM drivers WHERE account_id=%s and id = %s",
                    (account_id,driver_id)
                )
            except Exception as err:
                print("Error selecting drivers:", err)
                return ()
    

    async def delete_driver(self, driver_id, user_id, account_id) -> bool:
        try:
            return await self._execute(
                "DELETE FROM drivers WHERE id=%s  AND account_id=%s",
                (driver_id, account_id)
            )
        except Exception as err:
            print("Error deleting driver:", err)
            return False


    async def update_driver_status(self,account: str, status:bool,driver_id) -> bool:
            try:
                return await self._execute(
                    "UPDATE drivers SET in_route=%s WHERE account_id=%s AND id=%s",
                    (status, account, driver_id)
                )
            except Exception as err:
                print("Error updating driver status:", err)
                traceback.print_exc()
                return False
    

    async def update_driver(self, account: str, body: dict, driver_to_update: str):
        ALLOWED = {"name", "employee_number", "phone", "phone_secondary", "license_number", "license_expiry","photo_url","notes"}
        try:
            data = {k: v for k, v in body.items() if k in ALLOWED}
            if not data:
                return False

            fields = [f"{k} = %s" for k in data]
            values = (*data.values(), account, driver_to_update)

            return await self._execute(
                f"UPDATE drivers SET {', '.join(fields)} WHERE account_id=%s AND id=%s",
                values
            )
        except IntegrityError as err:
            return "DUPLICATE" if err.args[0] == 1062 else False
        except Exception as err:
            print("Error updating driver:", err)
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


    async def insert_trip(self, account_id, user_id, trip_information, stops) -> dict:
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await asyncio.wait_for(
                        cur.execute(
                            """INSERT INTO route_os_trip_assignments
                               (account_id, route_id, created_by, driver_id, driver_phone,vehicle_name,vehicle_plate,protocol_profile_id,folio,scheduled_departure)
                               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                            (account_id, trip_information["route_id"], user_id,
                             trip_information["driver_id"], trip_information["driver_phone"],trip_information["vehicle_name"],trip_information["vehicle_plate"],trip_information["protocol_profile_id"],trip_information["folio"],trip_information["scheduled_departure"])
                        ),
                        timeout=QUERY_TIMEOUT
                    )

                    await asyncio.wait_for(
                        cur.execute(
                            "SELECT id FROM route_os_trip_assignments WHERE display_id = LAST_INSERT_ID()"
                        ),
                        timeout=QUERY_TIMEOUT
                    )
                    row = await cur.fetchone()
                    trip_id = row[0]

                    stops_rows = [
                        (trip_id, s["waypoint_id"], s["sequence_order"], s["dwell_time"], s["expected_arrival"])
                        for s in stops
                    ]
                    await asyncio.wait_for(
                        cur.executemany(
                            """INSERT INTO route_os_trip_stops_log
                               (trip_assignment_id, waypoint_id, sequence_order, dwell_time, expected_arrival)
                               VALUES (%s,%s,%s,%s,%s)""",
                            stops_rows
                        ),
                        timeout=QUERY_TIMEOUT
                    )

            return {"created": True, "trip_id": trip_id}
        except IntegrityError as err:
            return {"created": False, "reason": "DUPLICATE" if err.args[0] == 1062 else "error"}
        except Exception as err:
            print("Error inserting trip:", err)
            return {"created": False, "reason": "error"}


    async def select_trips(self, account_id) -> tuple:
        try:
            return await self._fetch(
                """
                SELECT
                    t.id,
                    t.display_id,
                    t.vehicle_name,
                    t.status,
                    t.created_at,
                    r.route_name,
                    d.name AS driver_name,
                    u.username AS created_by_name
                FROM route_os_trip_assignments t
                JOIN routeos_os_routes r ON r.id = t.route_id
                JOIN drivers d ON d.id = t.driver_id
                JOIN route_os_users u ON u.id = t.created_by
                WHERE t.account_id = %s
                  AND t.deleted_at IS NULL
                ORDER BY t.created_at DESC
                """,
                (account_id,)
            )
        except Exception as err:
            print("Error selecting trips:", err)
            return ()


    async def delete_trip_assignment(self, account_id, trip_id) -> str | None:
        try:
            row = await self._fetch(
                "SELECT driver_id FROM route_os_trip_assignments WHERE account_id=%s AND id=%s",
                (account_id, trip_id),
                one=True
            )
            if not row:
                return None

            deleted = await self._execute(
                "DELETE FROM route_os_trip_assignments WHERE account_id=%s AND id=%s",
                (account_id, trip_id)
            )

            return row[0] if deleted else None
        except Exception as err:
            print("Error deleting trip assignment:", err)
            return None

    async def select_driver_photo_key(self, account: str, driver_id: str):
        try:
            result = await self._fetch(
                "SELECT photo_url FROM drivers WHERE account_id=%s AND id=%s",
                (account, driver_id)
            )
            return result
        except Exception as err:
            print("Error getting driver photo:", err)
            return False


    async def create_protocol_profile_mysql(self, profile_id, account_id, user_id, data, rule_rows, action_rows):
        try:
            async with self.transaction() as conn:
                await self.insert_protocol_profile(conn, profile_id, account_id, user_id, data)
                await self.insert_protocol_rules(conn, rule_rows)
                await self.insert_protocol_rule_actions(conn, action_rows)
            return profile_id
        except IntegrityError as err:
            return "DUPLICATE" if err.args[0] == 1062 else False
        except Exception as err:
            print("Error creating protocol profile:", err)
            return False

    async def insert_protocol_profile(self, conn, profile_id, account_id, user_id, data: dict):
        async with conn.cursor() as cur:
            if data["is_default"]:
                await asyncio.wait_for(
                    cur.execute(
                        "UPDATE protocol_profiles SET is_default=0 WHERE account_id=%s",
                        (account_id,)
                    ),
                    timeout=QUERY_TIMEOUT
                )
            await asyncio.wait_for(
                cur.execute(
                    """INSERT INTO protocol_profiles
                    (id, account_id, created_by, name, description, is_default)
                    VALUES (%s,%s,%s,%s,%s,%s)""",
                    (profile_id, account_id, user_id,
                    data["name"], data.get("description"), int(data["is_default"]))
                ),
                timeout=QUERY_TIMEOUT
            )

    async def insert_protocol_rules(self, conn, rule_rows: list):
        async with conn.cursor() as cur:
            await asyncio.wait_for(
                cur.executemany(
                    """INSERT INTO protocol_rules
                    (id, profile_id, rule_type, category, is_enabled, is_locked,
                        severity, risk_impact, threshold_value, threshold_unit, params)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    rule_rows
                ),
                timeout=QUERY_TIMEOUT
            )

    async def insert_protocol_rule_actions(self, conn, action_rows: list):
        if not action_rows:
            return
        async with conn.cursor() as cur:
            await asyncio.wait_for(
                cur.executemany(
                    """INSERT INTO protocol_rule_actions
                    (id, rule_id, action_type, delay_minutes, escalate, sort_order, config)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    action_rows
                ),
                timeout=QUERY_TIMEOUT
            )


    async def select_protocol_profiles(self, account_id) -> tuple:
        try:
            return await self._fetch(
                """
                SELECT
                    p.id,
                    p.display_id,
                    p.name,
                    p.description,
                    p.is_default,
                    p.created_at,
                    u.username AS created_by_name,
                    (SELECT COUNT(*) FROM protocol_rules r
                    WHERE r.profile_id = p.id AND r.is_enabled = 1) AS active_rules
                FROM protocol_profiles p
                JOIN route_os_users u ON u.id = p.created_by
                WHERE p.account_id = %s
                ORDER BY p.is_default DESC, p.created_at DESC
                """,
                (account_id,)
            )
        except Exception as err:
            print("Error selecting protocol profiles:", err)
            return ()

    async def delete_profile_protocol(self,account_id ,profile_id: str) -> bool:
        try:
            return await self._execute(
                "DELETE FROM protocol_profiles WHERE account_id = %s AND id = %s", (account_id,profile_id)
            )
        except Exception as err:
            print("Error deleting account:", err)
            return False

    async def select_clients_assinged(self, account_id,user_id) -> tuple:
        try:
            return await self._fetch(
                """
                SELECT 
                    u.username,
                    u.is_owner,
                    JSON_ARRAYAGG(
                        JSON_OBJECT(
                            'client_id', ca.client_id,
                            'client_name', ca.client_name
                        )
                    ) AS clients
                FROM route_os_users u
                LEFT JOIN clients_assigned ca 
                    ON ca.user_id = u.id 
                    AND ca.account_id = u.account_id
                WHERE u.account_id = %s AND u.id = %s
                GROUP BY u.id
                """,
                (account_id,user_id)
            )
        except Exception as err:
            print("Error selecting users:", err)
            return ()

    
    async def select_active_trips(
        self,
        account_id: str,
        *,
        f_client: str | None = None,
        f_plate: str | None = None,
        f_driver: str | None = None,
        f_status: str | None = None,
        f_date: str | None = None,
        f_q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple:
        try:
            HIDE_AFTER_MIN = 30

            where_clauses = []
            filter_params: list = []

            if f_client is not None:
                where_clauses.append("v.client_id = %s")
                filter_params.append(f_client)
            if f_plate is not None:
                where_clauses.append("v.vehicle_plate = %s")
                filter_params.append(f_plate)
            if f_driver is not None:
                where_clauses.append("v.driver_id = %s")
                filter_params.append(f_driver)
            if f_status is not None:
                where_clauses.append("v.display_status = %s")
                filter_params.append(f_status)
            if f_date is not None:
                where_clauses.append("DATE(v.scheduled_departure) = %s")
                filter_params.append(f_date)
            if f_q is not None:
                like = f"%{f_q}%"
                where_clauses.append(
                    "(v.folio LIKE %s OR v.vehicle_plate LIKE %s "
                    "OR v.driver_name LIKE %s OR v.employee_number LIKE %s)"
                )
                filter_params.extend([like, like, like, like])

            outer_where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            def visible(alias: str) -> str:
                return f"""{alias}.deleted_at IS NULL
                    AND (
                        {alias}.status IN ('scheduled', 'in_progress')
                        OR ({alias}.status IN ('completed', 'cancelled')
                            AND {alias}.updated_at >= NOW() - INTERVAL {HIDE_AFTER_MIN} MINUTE)
                    )"""

            query = f"""
                SELECT *
                FROM (
                    SELECT
                        t.id,
                        t.display_id,
                        t.account_id,
                        t.folio,
                        t.status                                                         AS trip_status,
                        t.vehicle_name,
                        t.vehicle_plate,

                        r.route_name,
                        r.client_id,
                        r.client_name,

                        d.id                                                             AS driver_id,
                        d.name                                                           AS driver_name,
                        d.employee_number,
                        d.photo_url,

                        t.protocol_profile_id,
                        pp.name                                                          AS protocol_name,

                        t.scheduled_departure                                            AS scheduled_departure,
                        s.real_departure,
                        s.eta_planned,
                        COALESCE(ls.eta_estimated, s.eta_planned)                       AS eta,
                        TIMESTAMPDIFF(
                            MINUTE,
                            t.scheduled_departure,
                            s.real_departure
                        )                                                                AS departure_delay_min,
                        COALESCE(s.delayed_stops, 0)                                    AS delayed_stops,
                        COALESCE(s.done_stops,    0)                                    AS done_stops,
                        COALESCE(s.total_stops,   0)                                    AS total_stops,

                        ls.phase,
                        ls.last_latitude,
                        ls.last_longitude,
                        ls.last_speed_kmh,
                        ls.last_position_at,

                        COALESCE(ev.risk_score, 0)                                      AS risk_score,
                        COALESCE(ev.open_events, 0)                                     AS open_events,

                        CASE
                            WHEN t.status = 'completed'            THEN 'completed'
                            WHEN t.status = 'cancelled'            THEN 'cancelled'
                            WHEN t.status = 'scheduled'            THEN 'pending'
                            WHEN COALESCE(ev.risk_score, 0) >= 50  THEN 'at_risk'
                            ELSE COALESCE(ls.phase, 'in_progress')
                        END                                                              AS display_status,

                        -- Minutos que faltan para ocultar el viaje (solo completados/cancelados)
                        CASE
                            WHEN t.status IN ('completed', 'cancelled')
                            THEN GREATEST(0, {HIDE_AFTER_MIN} - TIMESTAMPDIFF(MINUTE, t.updated_at, NOW()))
                        END                                                              AS hide_in_min,

                        (COALESCE(s.delayed_stops, 0) = 0)                              AS on_schedule

                    FROM route_os_trip_assignments t
                    JOIN routeos_os_routes   r  ON r.id  = t.route_id
                    JOIN drivers             d  ON d.id  = t.driver_id
                    JOIN protocol_profiles   pp ON pp.id = t.protocol_profile_id
                    LEFT JOIN trip_live_state ls ON ls.trip_assignment_id = t.id

                    LEFT JOIN (
                        SELECT e.trip_assignment_id,
                            LEAST(100, SUM(e.risk_impact)) AS risk_score,
                            COUNT(*)                        AS open_events
                        FROM trip_protocol_events e
                        JOIN route_os_trip_assignments a
                        ON a.id         = e.trip_assignment_id
                        AND a.account_id = %s
                        AND {visible('a')}
                        WHERE e.resolved_at IS NULL
                        GROUP BY e.trip_assignment_id
                    ) ev ON ev.trip_assignment_id = t.id

                    LEFT JOIN (
                        SELECT l.trip_assignment_id,
                            MAX(CASE WHEN l.sequence_order = 1 THEN l.actual_departure  END) AS real_departure,
                            MAX(l.expected_arrival)            AS eta_planned,
                            SUM(l.status = 'delayed')          AS delayed_stops,
                            SUM(l.actual_arrival IS NOT NULL)  AS done_stops,
                            COUNT(*)                           AS total_stops
                        FROM route_os_trip_stops_log l
                        WHERE l.trip_assignment_id IN (
                            SELECT a.id
                            FROM route_os_trip_assignments a
                            WHERE a.account_id = %s
                            AND {visible('a')}
                        )
                        GROUP BY l.trip_assignment_id
                    ) s ON s.trip_assignment_id = t.id

                    WHERE t.account_id = %s
                    AND {visible('t')}
                ) v
                {outer_where}
                ORDER BY (v.trip_status IN ('completed', 'cancelled')) ASC,
                        v.risk_score DESC,
                        v.scheduled_departure ASC
                LIMIT %s OFFSET %s
            """
            params = (account_id, account_id, account_id, *filter_params, limit, offset)

            return await self._fetch(query, params)

        except Exception as err:
            print("Error selecting active trips:", err)
            return ()


    async def select_active_trips_summary(self, account_id: str) -> tuple:
        try:
            return await self._fetch(
                """
                SELECT
                    COUNT(*)                               AS active_trips,
                    COALESCE(SUM(x.ds = 'at_risk'),  0)   AS in_risk,
                    COALESCE(SUM(x.ds = 'logistic'), 0)   AS logistic,
                    COALESCE(SUM(x.ds = 'pending'),  0)   AS slopes
                FROM (
                    SELECT CASE
                            WHEN t.status = 'scheduled'            THEN 'pending'
                            WHEN COALESCE(ev.risk_score, 0) >= 50  THEN 'at_risk'
                            ELSE COALESCE(ls.phase, 'in_progress')
                        END AS ds
                    FROM route_os_trip_assignments t
                    LEFT JOIN trip_live_state ls ON ls.trip_assignment_id = t.id
                    LEFT JOIN (
                        SELECT e.trip_assignment_id,
                            LEAST(100, SUM(e.risk_impact)) AS risk_score
                        FROM trip_protocol_events e
                        JOIN route_os_trip_assignments a
                        ON a.id         = e.trip_assignment_id
                        AND a.account_id = %s
                        AND a.deleted_at IS NULL
                        AND a.status IN ('scheduled', 'in_progress')
                        WHERE e.resolved_at IS NULL
                        GROUP BY e.trip_assignment_id
                    ) ev ON ev.trip_assignment_id = t.id
                    WHERE t.account_id = %s
                    AND t.deleted_at IS NULL
                    AND t.status IN ('scheduled', 'in_progress')
                ) x
                """,
                (account_id, account_id),
                one=True
            )
        except Exception as err:
            print("Error selecting active trips summary:", err)
            return ()

    async def update_trip_status(self, account_id: str, trip_id: str, status: str) -> bool:
        try:
            return await self._execute(
                "UPDATE route_os_trip_assignments SET status=%s WHERE account_id=%s AND id=%s",
                (status,account_id, trip_id)
            )
        except Exception as err:
            print("Error updating status:", err)
            traceback.print_exc()
            return False


    async def select_active_trips_summary(self, account_id: str) -> tuple:
        try:
            return await self._fetch(
                """
                SELECT
                    COUNT(*)                               AS active_trips,
                    COALESCE(SUM(x.ds = 'at_risk'),  0)   AS in_risk,
                    COALESCE(SUM(x.ds = 'logistic'), 0)   AS logistic,
                    COALESCE(SUM(x.ds = 'pending'),  0)   AS slopes
                FROM (
                    SELECT CASE
                            WHEN t.status = 'scheduled'            THEN 'pending'
                            WHEN COALESCE(ev.risk_score, 0) >= 50  THEN 'at_risk'
                            ELSE COALESCE(ls.phase, 'in_progress')
                        END AS ds
                    FROM route_os_trip_assignments t
                    LEFT JOIN trip_live_state ls ON ls.trip_assignment_id = t.id
                    LEFT JOIN (
                        SELECT e.trip_assignment_id,
                            LEAST(100, SUM(e.risk_impact)) AS risk_score
                        FROM trip_protocol_events e
                        JOIN route_os_trip_assignments a
                        ON a.id         = e.trip_assignment_id
                        AND a.account_id = %s
                        AND a.deleted_at IS NULL
                        AND a.status IN ('scheduled', 'in_progress','completed')
                        WHERE e.resolved_at IS NULL
                        GROUP BY e.trip_assignment_id
                    ) ev ON ev.trip_assignment_id = t.id
                    WHERE t.account_id = %s
                    AND t.deleted_at IS NULL
                    AND t.status IN ('scheduled', 'in_progress','completed')
                ) x
                """,
                (account_id, account_id),
                one=True
            )
        except Exception as err:
            print("Error selecting active trips summary:", err)
            return ()

    async def update_trip_status(self, account_id: str, trip_id: str, status: str) -> bool:
        try:
            return await self._execute(
                "UPDATE route_os_trip_assignments SET status=%s WHERE account_id=%s AND id=%s",
                (status,account_id, trip_id)
            )
        except Exception as err:
            print("Error updating password:", err)
            traceback.print_exc()
            return False

    async def select_vehicle_information_for_trip(self,account_id:str,trip_id:str) -> tuple:
        try:
            return await self._fetch(
                """SELECT
                    route_trip.vehicle_name,
                    route_trip.vehicle_plate,
                    route_os.id,
                    route_os.client_name,
                    route_os.client_id,
                    route_trip.driver_id
                FROM route_os_trip_assignments AS route_trip
                LEFT JOIN routeos_os_routes AS route_os
                    ON route_trip.route_id = route_os.id 
                    WHERE  route_trip.account_id = %s and route_trip.id = %s
                    """ ,(account_id,trip_id)
            )
        except Exception as err:
            print("Error selecting vehicle information for trip:", err)
            return ()

    async def select_stops_information(self,trip_id:str) -> tuple:
        try:
            return await self._fetch(
                """SELECT r_logs.sequence_order,wpy.label,poi.latitude,poi.longitude,r_logs.expected_arrival, 
                        r_logs.status FROM route_os_trip_stops_log AS r_logs left join 
                        route_os_waypoints as wpy ON r_logs.waypoint_id = wpy.id
                        left join points_of_interest as poi ON wpy.poi_id= poi.id 
                        where r_logs.trip_assignment_id = %s;
                    """ ,(trip_id,)
            )
        except Exception as err:
            print("Error selecting stops information:", err)
            return ()


    async def select_driver_trips(self,driver_id:str,account_id:str) -> tuple:
        try:
            return await self._fetch(
                """SELECT
                        trips.folio,
                        trips.vehicle_name,
                        trips.vehicle_plate,
                        trips.scheduled_departure,
                        rlogs.expected_arrival,
                        trips.status
                    FROM route_os_trip_assignments AS trips
                    LEFT JOIN route_os_trip_stops_log AS rlogs
                        ON trips.id = rlogs.trip_assignment_id
                        AND rlogs.sequence_order = (
                            SELECT MAX(rl.sequence_order)
                            FROM route_os_trip_stops_log AS rl
                            WHERE rl.trip_assignment_id = trips.id
                        )
                    WHERE trips.driver_id = %s and trips.account_id=%s;
                    """ ,(driver_id,account_id)
            )
        except Exception as err:
            print("Error selecting driver trips:", err)
            return ()

    async def select_enterprise_id_by_route(self, account_id,route_id) -> tuple:
        try:
            return await self._fetch(
                "SELECT id,client_name,client_id FROM routeos_os_routes WHERE account_id=%s and id = %s",
                (account_id,route_id)
            )
        except Exception as err:
            print("Error selecting enterprise id for route:", err)
            return ()
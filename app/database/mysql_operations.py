import asyncmy
from asyncmy.pool import Pool
from asyncmy.errors import IntegrityError
from control.configuration import Config
import asyncio

import traceback

class MysqlOperations:
    _pool: Pool = None
    _lock = asyncio.Lock()

    @classmethod
    async def _get_pool(cls):
        if cls._pool is None:
            async with cls._lock:
                if cls._pool is None:  
                    cls._pool = await asyncmy.create_pool(
                        host=Config.DB_HOST,
                        db=Config.DB_NAME,
                        user=Config.DB_USER,
                        password=Config.DB_PASSWORD,
                        charset="utf8mb4",
                        maxsize=5
                    )
        return cls._pool

    async def select_accounts(self, slug_account:str) -> tuple:
        try:
            pool = await self._get_pool()  
            async with pool.acquire() as connection:
                async with connection.cursor() as cursor:
                    query = "SELECT * FROM accounts WHERE slug = %s"
                    await cursor.execute(query, (slug_account,))
                    results = await cursor.fetchall()
                    if results and len(results)> 0:
                        return results
        except Exception as err:
            print("Error selecting accounts:", err)
            return ()
    
    async def insert_user(self,user_information,account_uuid,password_hash) -> bool:
        try:
            pool = await self._get_pool()  
            async with pool.acquire() as connection:
                async with connection.cursor() as cursor:
                    query = """INSERT INTO 
                                route_os_users(account_id,name,username,email,phone,password_hash,recovery_email,role)
                                VALUES(%s,%s,%s,%s,%s,%s,%s,%s)"""

                    await cursor.execute(query,(account_uuid,user_information["name"],user_information["username"],user_information["email"],user_information["phone"],password_hash,user_information["recovery_email"],user_information["role"]))
                    await connection.commit()
                    if cursor.rowcount>0:
                        return True
                    else:
                        return False
        except IntegrityError as err:
            if err.args[0] == 1062:
                return "DUPLICATE"
            return False
        except Exception as err:
            print("Error inserting user in table: ",err)
            return False
    
    async def select_user(self, user:str, account:str) -> tuple:
        try:
            pool = await self._get_pool()  
            async with pool.acquire() as connection:
                async with connection.cursor() as cursor:
                    query = "SELECT username,password_hash,id , role FROM route_os_users WHERE username= %s and account_id=%s" 
                    await cursor.execute(query,(user,account))
                    results = await cursor.fetchall()
                    if results and len(results)> 0:
                        return results
        except Exception as err:
            print("Error selecting the user: ",err)
            return ()
        
    

    async def update_user(self, account: str, body: dict, user_to_update: str) -> bool:
        try:
            pool = await self._get_pool()  
            async with pool.acquire() as connection:
                async with connection.cursor() as cursor:
                    
                    fields = []
                    values = []
                    
                    for key, value in body.items():
                        fields.append(f"{key} = %s")
                        values.append(value)
                    values.append(account)
                    values.append(user_to_update)
                    
                    query = f"UPDATE route_os_users SET {', '.join(fields)} WHERE account_id = %s AND username = %s"
                    
                    
                    await cursor.execute(query, tuple(values))
                    await connection.commit()
                    
                    return cursor.rowcount > 0
        
        except IntegrityError as err:
            if err.args[0] == 1062:
                return "DUPLICATE"
            return False

        except Exception as err:
            print("Error updating user:", err)
            return False
    

    async def delete_user(self, account: str, username: str) -> bool:
        try:
            pool = await self._get_pool()
            async with pool.acquire() as connection:
                async with connection.cursor() as cursor:
                    query = "DELETE FROM route_os_users WHERE account_id = %s AND username = %s"
                    await cursor.execute(query, (account, username))
                    await connection.commit()
                    return cursor.rowcount > 0
        except Exception as err:
            print("Error deleting user:", err)
            return False
    
    async def select_user_email(self, email:str, account:str) -> tuple:
        try:
            pool = await self._get_pool()  
            async with pool.acquire() as connection:
                async with connection.cursor() as cursor:
                    query = "SELECT username,password_hash,id , role FROM route_os_users WHERE email= %s and account_id=%s" 
                    await cursor.execute(query,(email,account))
                    results = await cursor.fetchall()
                    if results and len(results)> 0:
                        return results
        except Exception as err:
            print("Error selecting the user: ",err)
            return ()
    
    async def insert_token(self, user_id: str, token: str):
        try:
            pool = await self._get_pool()
            async with pool.acquire() as connection:
                async with connection.cursor() as cursor:
                    query = """
                        INSERT INTO route_os_password_resets (user_id, token, expires_at)
                        VALUES (%s, %s, NOW() + INTERVAL 1 HOUR)
                    """
                    await cursor.execute(query, (user_id, token))
                    await connection.commit()
                    return True
        except Exception as e:
            print("Error saving recovery token:", e)
            return False
    
    async def select_token(self, token:str) -> tuple:
        try:
            pool = await self._get_pool()  
            async with pool.acquire() as connection:
                async with connection.cursor() as cursor:
                    query = "SELECT * FROM route_os_password_resets WHERE token=%s and used=%s AND expires_at > NOW()" 
                    await cursor.execute(query,(token,0))
                    return await cursor.fetchone() 
        except Exception as err:
            print("Error selecting the user: ",err)
            return None
    

    async def update_password(self,user_id:str,new_password:str,account:str) -> bool:
        try:
            pool = await self._get_pool()  
            async with pool.acquire() as connection:
                async with connection.cursor() as cursor:
                    query = "UPDATE route_os_users SET password_hash= %s WHERE account_id= %s and id=%s" 
                    await cursor.execute(query,(new_password,account,user_id)) 
                    await connection.commit()                    
                    return True if cursor.rowcount>0 else False
        except Exception as err:
            print("Error inserting user in table: ",err)
            traceback.print_exc()
            return False
    
    async def token_status(self, token:str) -> bool:
        try:
            pool = await self._get_pool()  
            async with pool.acquire() as connection:
                async with connection.cursor() as cursor:
                    query = "UPDATE route_os_password_resets SET used= %s WHERE token=%s" 
                    await cursor.execute(query,(1,token)) 
                    await connection.commit()                    
                    return True if cursor.rowcount>0 else False
        except Exception as err:
            print("Error inserting user in table: ",err)
            traceback.print_exc()
            return False
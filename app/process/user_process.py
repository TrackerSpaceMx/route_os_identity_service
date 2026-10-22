
import bcrypt
import resend
from database.operations_db import OperationsDB
from control.configuration import Config
import httpx
import secrets


class UserProcess:
    def __init__(self):
        self.__dbOPerations= OperationsDB()
        self._clients_endpoint = "https://ws.fulltrack2.com/clients/all/apiKey/"
    

    @staticmethod
    def encrypt_password(password):
        password_hashed = bcrypt.hashpw(password.encode("utf-8"),bcrypt.gensalt())
        password_decoded = password_hashed.decode("utf-8")
        return password_decoded 

    async def save_last_access(self,user_id,account_id):
        try:
            update_login_response = await self.__dbOPerations.update_last_login_in_table(user_id,account_id)
        except Exception as err:
            print("Error updating the last status from user: ",err)   

    async def create_user(self,account_id,user_information,is_owner=0):
        try:
            account_id
            password_hash = UserProcess.encrypt_password(user_information["password_hash"])
            user_insertion = await self.__dbOPerations.insert_user_in_table(account_id,user_information,password_hash,is_owner)
            
            if "send_invitation" in user_information and user_information["send_invitation"] == True:
                if user_insertion  and user_insertion!="DUPLICATE":
                    user_id_response = await self.__dbOPerations.get_user_by_display_id(user_insertion,account_id,user_information["username"])
                email_invitation = await self.set_password_process(user_id_response,user_information["email"],user_information["username"])
            return user_insertion
        except Exception as err:
            print("Error creating user: ",user_information,err)
            return False
    

    async def authenticate_user(self,user_data,account):
        authentication_result = False
        try:
            user_validation = await self.__dbOPerations.validate_user_from_table(user_data,account)
            if user_validation:
                authentication_result = user_validation
        except Exception as err:
            print("Error validating user: ",err)
            return  False
        return authentication_result

    
    async def get_account_from_slug(self,slug):
        try:
            response = await self.__dbOPerations.get_account(slug)
            return response
        except Exception  as err:
            print("Error getting the slug:",err)
            return None
    
    async def update_user_by_id(self,account: str, body:dict,user_to_update:str):
        try:
            valid_keys_to_update = ("name","username","email","phone","password_hash","recovery_email","status","clients_information")
            keys_to_update = [key for key in body.keys()]
            for key in keys_to_update:
                if key not in valid_keys_to_update:
                    return False
                
            if "password_hash" in body:
                body["password_hash"] = UserProcess.encrypt_password(body.get("password_hash"))
            update_result = await self.__dbOPerations.update_user(account,body,user_to_update)
            if update_result:
                return update_result       
        except Exception as err:
            print("Error updating the user: ",err)
            return False
    
    async def delete_user_from_table(self,account,user):
        try:
            delete_result = await self.__dbOPerations.delete_user_from_database(account,user)
            if delete_result:
                return delete_result
        except Exception as err:
            print("Error deleting the user: ",user)
            return False
    

    async def send_recovery_email(self,to: str, token: str, slug: str):
        resend.api_key = Config.RESEND_API_KEY
        try:
            reset_link = f"http://localhost:5174/reset-password?token={token}"
            
            resend.Emails.send({
                "from": "onboarding@resend.dev",
                "to": to,
                "subject": "Recupera tu contraseña",
                "html": f"""
                    <h2>Recuperación de contraseña</h2>
                    <p>Click en el botón para resetear tu contraseña.</p>
                    <a href='{reset_link}' 
                    style='background:#000;color:#fff;padding:12px 24px;
                            border-radius:6px;text-decoration:none'>
                    Resetear contraseña
                    </a>
                    <p>Este link expira en 1 hora.</p>
                    <p>Si no solicitaste esto, ignora este correo.</p>
                """
            })
            return True
        except Exception as e:
            print("Error sending email:", e)
            return False

    async def set_password_process(self,user_id,to:str,username):
        token = secrets.token_urlsafe(32)
        token_insertion_response= await self.__dbOPerations.save_token_to_reset_password(user_id,token,"invite")
        if token_insertion_response:
            welcome_email = await self.send_welcome_email(to, username,token)

    async def send_welcome_email(self, to: str, username: str,token:str):
        resend.api_key = Config.RESEND_API_KEY
        try:
            reset_link = f"http://localhost:5174/reset-password?token={token}"
            
            resend.Emails.send({
                "from": "onboarding@resend.dev",
                "to": to,
                "subject": "Tu cuenta ha sido creada",
                "html": f"""
                    <h2>¡Bienvenido, {username}!</h2>
                    <p>Tu cuenta en el sistema Route OS ha sido creada exitosamente.</p>
                    <p>Crea tu contraseña de acceso mediante el siguiente link, este enlace expira en 1 hora, 
                    <a href='{reset_link}'
                    style='background:#000;color:#fff;padding:12px 24px;
                            border-radius:6px;text-decoration:none'>
                    Ir al sistema
                    </a>
                """
            })
            return True
        except Exception as e:
            print("Error sending welcome email:", e)
            return False
    
    async def get_user_by_email(self,email,account_id):
        try:
            user_response=await  self.__dbOPerations.query_user_by_email(email,account_id)
            if user_response:
                response= {"id":user_response[0][2]}   
                return response
        except Exception as err:
            print("Error getting the user by email")
            return False
    
    async def save_recovery_token(self,user_id,token):
        try:
            token_insertion_response= await self.__dbOPerations.save_token_to_reset_password(user_id,token,"reset")
        except Exception as err:
            print("Error saving token in table:",err)

    async def get_recovery_token(self,token):
        try:
            token_result = await self.__dbOPerations.get_token_data(token)
            return token_result
        except Exception as err:
            print("Error getting token: ",err)
            return False
    
    async def update_password_process(self,user_id:str,new_password:str,acccount:str,token:str):
        try:
            new_password_hashed =  UserProcess.encrypt_password(new_password)
            update_process_response = await self.__dbOPerations.update_new_password_and_set_token_as_used(user_id,new_password_hashed,acccount,token)            
        except Exception as err:
            print("Error updating the new password: ",err)
            return False
    

    async def get_users(self,account_id):
        try:
            users_response = await self.__dbOPerations.get_users_from_account(account_id)
            return users_response
        except Exception as err:
            print("Error getting the users from table",err)
            return False


    async def get_clients_from_fulltrack(self,account_id):
        
        try:
            api_key,secret_key = await self.get_fulltrack_keys(account_id)
            url = f"{self._clients_endpoint}{api_key}/secretKey/{secret_key}"
            async with httpx.AsyncClient() as client:
                clients = []
                response = await client.get(url=url)
                if response.status_code !=200:
                    return False
                response_json = response.json()
                data = response_json.get("data")
                if len(data) <=0:
                    return False
                for client in data:
                    client_information = {"id":client["ras_cli_id"],"name":client["ras_cli_desc"]}
                    clients.append(client_information)
                if len(clients)>0:
                    return clients
                else:
                    return "NO_CONTENT"

        except Exception as err:
            print("Error getting the clients",err)
            return False


    async def get_fulltrack_keys(self,account_id):
        try:
            api_key,secret_key= await self.__dbOPerations.get_keys_from_table(account_id)
            return api_key,secret_key
        except Exception as err:
            print("Error getting the fulltrack keys: ",err)

import bcrypt
import resend
from database.operations_db import OperationsDB
from control.configuration import Config


class UserProcess:
    def __init__(self):
        self.__dbOPerations= OperationsDB()
    

    @staticmethod
    def encrypt_password(password):
        password_hashed = bcrypt.hashpw(password.encode("utf-8"),bcrypt.gensalt())
        password_decoded = password_hashed.decode("utf-8")
        return password_decoded    

    async def create_user(self,account_id,user_information):
        try:
            account_id
            password_hash = UserProcess.encrypt_password(user_information["password_hash"])
            return await self.__dbOPerations.insert_user_in_table(account_id,user_information,password_hash)
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
    
    async def update_user_by_username(self,account: str, body:dict,user_to_update:str):
        try:
            valid_keys_to_update = ("name","username","email","phone","password_hash","recovery_email","status")
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
            reset_link = f"http://localhost:5173/reset-password?token={token}"
            
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
            token_insertion_response= await self.__dbOPerations.save_token_to_reset_password(user_id,token)
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
            print("Error getting the users from table")
            return False
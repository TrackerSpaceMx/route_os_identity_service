from database.mysql_operations import MysqlOperations
import bcrypt

class OperationsDB:
    def __init__(self):
        self.__mysqlOperations = MysqlOperations()

    def validate_password(self, password_input,password_hash):
        password_input_encoded = password_input.encode("utf-8")
        password_hash_encoded = password_hash.encode("utf-8")
        if bcrypt.checkpw(password_input_encoded,password_hash_encoded):
            return True
        else:
            return False

    async def get_account(self,slug:str):
        return await self.__mysqlOperations.select_accounts(slug)

    async def insert_user_in_table(self, account_id,user_information,password_hash):
        uuid_account= account_id
        if not uuid_account:
            return False
        return await self.__mysqlOperations.insert_user(user_information,uuid_account,password_hash)
        

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
        
    
    async def update_user(self,account: str, body:dict,user_to_update:str):
        result = False
        update_result = await self.__mysqlOperations.update_user(account, body,user_to_update)
        if update_result:
            result = update_result
        return result
    

    async def delete_user_from_database(self, account:str, username:str):
        return await self.__mysqlOperations.delete_user(account,username)
    

    async def query_user_by_email(self, email,account_id):
        user_response = await self.__mysqlOperations.select_user_email(email,account_id)
        if user_response and len(user_response)>0:
            return user_response
        return False
    
    async def save_token_to_reset_password(self,user_id,token):
        return await self.__mysqlOperations.insert_token(user_id,token)


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
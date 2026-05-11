from database.operations_db import OperationsDB

class AccountProcess:
    def __init__(self):
        self.__dbOperations = OperationsDB()
    

    async def authenticate_user_account(self,user):
        authentication_result = False
        try:
            user_validation = await self.__dbOperations.validate_user_from_table_account(user)
            if user_validation:
                authentication_result = user_validation
        except Exception as err:
            print("Error authenticating user",err)
            return False
        return authentication_result

    async def validate_user_permission(self,user_id,username):
        try:
            user_validation_response = await self.__dbOperations.select_account_user_by_id_and_username(user_id,username)
            return user_validation_response
        except Exception as err:
            print("Error validating the user: ",err)
            return False
    
    async def register_account(self,account_information):
        try:
            slug = account_information["slug"]          
            slug_modified = slug.replace(" ","")
            account_information["slug"] = slug_modified
            account_result= await self.__dbOperations.register_account_in_table(account_information)
            return account_result
        except Exception as err:
            print("Error registering acccount:",err)
            return False
    
    async def delete_account_from_table(self,account):
        try:
            response = await self.__dbOperations.delete_account_from_table_with_users(account)
            return response
        except Exception as err:
            print("Error deleting account: ",err)
            return False
    
    async def get_accounts_list(self):
        try:
            accounts = await self.__dbOperations.get_accounts_from_table()
            return accounts
        except Exception as err:
            print("Error getting the accounts:",err)
            return False
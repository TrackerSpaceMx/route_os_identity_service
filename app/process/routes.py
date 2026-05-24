from fastapi import FastAPI,status,HTTPException,Depends,Request,Response
from fastapi.responses import JSONResponse
from scalar_fastapi import get_scalar_api_reference
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from jose import JWTError,jwt
from datetime import datetime,timedelta
from models.schemas import Users,UserAuthentication,UpdateUser,RecoveryPassword,ResetPassword,Account,PointsOfInterest,RoutesCreation
from control.configuration import Config
from process.user_process import UserProcess
from process.account_process import AccountProcess
from process.routes_process import RoutesProcess
from starlette.middleware.base import BaseHTTPMiddleware
import secrets



app = FastAPI()
user_process = UserProcess()
account_process = AccountProcess()
routes_process = RoutesProcess()


origins = [
    "http://localhost:5173",
    "http://localhost:5174"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE","PATCH"], 
    allow_headers=["Authorization", "Content-Type"],
)
security = HTTPBearer()


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        excluded_paths = [
            "/auth/account/user",
            "/auth/verify/account",
            "/account",
            "/accounts",
            "/scalar",
            "/docs",
            "/openapi.json"
        ]
        if request.url.path in excluded_paths:
            return await call_next(request)
        
        host = request.headers.get("host") 
        slug = host.split(".")[0]     
        slug = "pslog"      
        print("Slug:",slug)
        
        account = await user_process.get_account_from_slug(slug)
        
        if not account:
            return JSONResponse( 
                status_code=404, 
                content={"message": "Account not found"}
            )
        
        request.state.account = account
        
        response = await call_next(request)
        return response

app.add_middleware(TenantMiddleware)


def create_token(data: dict):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=Config.TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, Config.SECRET_KEY, algorithm="HS256")


@app.get("/auth/verify", status_code=status.HTTP_200_OK)
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        return {"valid": True, "user": payload.get("sub")}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid token or expired"}
        )
    
@app.post("/auth/user",status_code=status.HTTP_200_OK)
async def authenticate_user(body: UserAuthentication,request:Request):
    account = request.state.account
    account_uuid= account[0][0]
    user = body.model_dump()
    user_validation = await user_process.authenticate_user(user,account_uuid)
    if not user_validation :
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail={"message":"unauthorized access"})
    
    token = create_token({"sub": user["username"],"user_id":user_validation["id"],"role":user_validation["role"]})
    return {"token": token}


@app.get("/auth/verify/account", status_code=status.HTTP_200_OK)
def verify_token_account(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        return {"valid": True, "user": payload.get("sub")}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid token or expired"}
        )


@app.post("/auth/account/user",status_code=status.HTTP_200_OK)
async def authenticate_user_account_request(body: UserAuthentication):
    user = body.model_dump()
    user_validation = await account_process.authenticate_user_account(user)
    if not user_validation :
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail={"message":"unauthorized access"})
    
    token = create_token({"sub": user["username"],"user_id":user_validation["id"]})
    return {"token": token}




@app.post("/auth/recovery", status_code=status.HTTP_200_OK)
async def recovery_password(body: RecoveryPassword, request: Request):
    account = request.state.account
    account_uuid = account[0][0]
    
    user = await user_process.get_user_by_email(body.email,account_uuid)
    
    if not user:
        return {"message": "If the correo exists, you will receive an email"}
    
    token = secrets.token_urlsafe(32)
    await user_process.save_recovery_token(user["id"], token)

    print("TOKEN TEST:", token)
    await user_process.send_recovery_email(body.email,token,"local")
    
    return {"message": "If the correo exists, you will receive an email"}


@app.post("/auth/reset", status_code=status.HTTP_200_OK)
async def reset_password(body: ResetPassword,request:Request):
    token_data = await user_process.get_recovery_token(body.token)
    account = request.state.account
    account_uuid= account[0][0]    
    if not token_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                          detail={"message": "Invalid token or expired"})
    
    await user_process.update_password_process(token_data["user_id"], body.new_password,account_uuid,body.token)
  
    return {"message": "Password successfully reset"}



@app.post("/users",status_code=status.HTTP_201_CREATED)
async def create_user(body:Users,request:Request,credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        role = payload.get("role")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                          detail={"message": "Not enough permissions"})
    user = body.model_dump()    
    account = request.state.account
    account_uuid= account[0][0]
    user_response= await user_process.create_user(account_uuid,user)
    if user_response =="DUPLICATE":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail={"message":"user already created"})
    if not user_response:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"message":"Error creating user"})
    return {"message":"User created successfully"}

@app.get("/users",status_code=status.HTTP_200_OK)
async def get_users(request:Request,credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        role = payload.get("role")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    account = request.state.account
    account_uuid = account[0][0]
    users = await user_process.get_users(account_uuid)
    if not users:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"message":f"Server error"})
    return {"data":users}

@app.patch("/users/{username}",status_code=status.HTTP_200_OK)
async def patch_user(username:str,body:UpdateUser, request:Request,credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        role = payload.get("role")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                          detail={"message": "Not enough permissions"})

    account = request.state.account
    account_uuid = account[0][0]
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                          detail={"message": "No fields to update"})

    update_response = await user_process.update_user_by_username(account_uuid,update_data,username)
    if not update_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message":"User not found"})

    if update_response == "DUPLICATE":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail={"message":"user already created"})
    
    return {"message":"User updated successfully"}
    

@app.delete("/users/{username}",status_code=status.HTTP_200_OK)
async def delete_user(username:str,request:Request,credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        role = payload.get("role")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                          detail={"message": "Not enough permissions"})
    
    account = request.state.account
    account_uuid = account[0][0]
    delete_result= await user_process.delete_user_from_table(account_uuid,username)
    if not delete_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message":f"User {username} not found"})
    if delete_result == "FORBIDDEN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Admin can't be deleted"}
        )

    return {"message":f"User {username} deleted successfully"}

@app.post("/account", status_code=status.HTTP_201_CREATED)
async def create_account(body: Account, credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        username = payload.get("sub")
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid token or expired"}
        )

    body_information = body.model_dump()
    validate_user = await account_process.validate_user_permission(user_id,username)
    if not validate_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Not enough permissions"}
        )
    
    create_account_response = await account_process.register_account(body_information)

    if create_account_response =="DUPLICATE":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail={"message":"Account already created"})
    
    elif create_account_response == "Unauthorized":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,detail={"message":"invalid keys"})

    return {"message":"Account created successfully"}


@app.delete("/account/{slug_account}", status_code=status.HTTP_200_OK)
async def delete_account(slug_account, credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        username = payload.get("sub")
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid token or expired"}
        )

    validate_user = await account_process.validate_user_permission(user_id,username)
    if not validate_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Not enough permissions"}
        )
    
    print("slug to delete: ",slug_account)
    delete_account_result = await account_process.delete_account_from_table(slug_account)  
    if not delete_account_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message":f"Account {slug_account} not found"})

    return {"message":f"Account {slug_account} deleted successfully"}



@app.get("/accounts",status_code=status.HTTP_200_OK)
async def get_accounts(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        username = payload.get("sub")
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid token or expired"}
        )

    validate_user = await account_process.validate_user_permission(user_id,username)
    if not validate_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Not enough permissions"}
        )
    accounts_response = await account_process.get_accounts_list()
    
    if not accounts_response:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"message":f"Server error"})
    
    if accounts_response == "NO_CONTENT":
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    
    return {"data": accounts_response}



@app.post("/points",status_code=status.HTTP_201_CREATED)
async def create_user(body:PointsOfInterest,request:Request,credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        role = payload.get("role")
        user_id = payload.get("user_id")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                          detail={"message": "Not enough permissions"})
    point_information = body.model_dump()
    account = request.state.account
    account_uuid= account[0][0]
    point_response= await routes_process.create_point(point_information,account_uuid,user_id)
    if not point_response:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"message":"Error creating point"})
    
    if point_response =="DUPLICATE":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail={"message":"Point already created"})
    return {"message":"Point created successfully"}



@app.get("/points",status_code=status.HTTP_200_OK)
async def get_users(request:Request,credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        role = payload.get("role")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    account = request.state.account
    account_uuid = account[0][0]
    points_response = await routes_process.get_points(account_uuid)

    if points_response == "NO_CONTENT":
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    if not points_response:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"message":f"Server error"})
    return {"data":points_response}



@app.delete("/points/{point_id}",status_code=status.HTTP_200_OK)
async def delete_point(point_id:str,request:Request,credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        role = payload.get("role")
        user_id = payload.get("user_id")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                          detail={"message": "Not enough permissions"})
    
    account = request.state.account
    account_uuid = account[0][0]
    delete_result= await routes_process.remove_point(point_id,user_id,account_uuid)
    if not delete_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message":f"Point {point_id} not found"})


    return {"message":f"Point {point_id} deleted successfully"}


@app.post("/routes",status_code=status.HTTP_201_CREATED)
async def create_user(body:RoutesCreation,request:Request,credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        role = payload.get("role")
        user_id = payload.get("user_id")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                          detail={"message": "Not enough permissions"})
    route_body = body.model_dump()
    account = request.state.account
    account_uuid= account[0][0]
    route_response= await routes_process.create_route(route_body,account_uuid,user_id)
    if not route_response:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail={"message":"Error creating route"})

    if route_response =="DUPLICATE":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail={"message":"Route already created"})
    return {"message":"Route created successfully"}


    
@app.get("/scalar",include_in_schema=False)
def get_scalar_docs():
    return get_scalar_api_reference(openapi_url=app.openapi_url,title="Documentation")


from process.routes import app
import uvicorn
from control.configuration import Config


if __name__ == "__main__":
    uvicorn.run(app,host=Config.API_HOST,port=Config.API_PORT)




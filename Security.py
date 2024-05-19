from decouple import config
import datetime
import jwt
import pytz

class Security():

    secret = config('JWT_KEY')
    tz = pytz.timezone("America/Santiago")
    
    @classmethod
    def generate_Token(cls,user, password, rol):
        payload = {
            'iat': datetime.datetime.now(tz=cls.tz),
            'exp': datetime.datetime.now(tz=cls.tz) + datetime.timedelta(minutes=10),
            'username':user,
            'password':password,
            'rol':rol
        }
        return jwt.encode(payload,cls.secret,algorithm="HS256")
    
    @classmethod
    def validar_token(cls, headers):
        if 'Authorization' in headers.keys():
            authorization = headers['Authorization']
            encode_token = authorization.split(" ")[1]
            try:
                payload = jwt.decode(encode_token,cls.secret,algorithms=["HS256"])
                return True
            except (jwt.ExpiredSignatureError, jwt.InvalidSignatureError):
                return False
            
        return False
                



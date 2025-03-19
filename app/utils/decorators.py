import jwt
import requests
from jwt.algorithms import RSAAlgorithm
from functools import wraps
from quart import current_app, request, jsonify, g
from app.utils.log_utils import get_logger

logger = get_logger("aoai_backend")


async def verify_token(token):
    TENANT_ID = current_app.config["MSAL_TENANT_ID"]
    CLIENT_ID = current_app.config["MSAL_CLIENT_ID"]
    OPENID_CONFIG_URL = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"
    ISSUER = f"https://sts.windows.net/{TENANT_ID}/"
    try:
        jwks = requests.get(OPENID_CONFIG_URL).json()
        public_keys = {key['kid']: key for key in jwks['keys']}
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        if kid not in public_keys:
            raise ValueError("Invalid 'kid' in token header")
        rsa_key = RSAAlgorithm.from_jwk(public_keys[kid])

        decoded_token = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=CLIENT_ID,
            issuer=ISSUER
        )
        return decoded_token, None, None
    except jwt.ExpiredSignatureError:
        return None, 401, "Token has expired"
    except jwt.InvalidIssuerError:
        return None, 401, "Invalid issuer"
    except jwt.InvalidTokenError as e:
        logger.exception(e)
        return None, 401, "Invalid token"


def token_required(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "Missing authorization header"}), 401

        try:
            token = auth_header.split(" ")[1]  # 从 "Bearer <token>"
        except IndexError:
            return jsonify({"error": "Invalid authorization header format"}), 401

        token_data, status, message = await verify_token(token)
        if status == 401:
            return jsonify({"error": message}), 401

        g.email = token_data.get('email') or token_data.get('upn')
        family_name = token_data.get('family_name')
        given_name = token_data.get('given_name')
        if family_name is None and given_name is None:
            g.username = "不明"
        else:
            g.username = (family_name or "") + " " + (given_name or "")

        return await f(*args, **kwargs)

    return decorated_function

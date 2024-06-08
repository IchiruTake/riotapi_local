import os

# ==================================================================================================
# Re-declaration of constants
_MINUTE: int = 60



# ==================================================================================================
# Environment variables
ENV_PROFILE = os.getenv("RIOTAPI_ENV_PROFILE", "DEV")

if ENV_PROFILE == "DEV":
    REFRESH_RATE_IF_NOT_FOUND: int = 5 * _MINUTE  # 5 minutes
    MIN_REFRESH_RATE_IF_FOUND: int = 1 * _MINUTE  # 1 minutes
    RIOTAPI_ENV_CFG_FILE: str = "./conf/riotapi.env.toml"
    RIOTAPI_SECRETS_CFG_FILE: str = "./conf/riotapi.secrets.toml"
    RIOTAPI_GC_CFG_FILE: str = "./conf/riotapi.gc.toml"
    RIOTAPI_LOG_CFG_FILE: str = "./conf/riotapi.log.yaml"
elif ENV_PROFILE == "PROD":
    REFRESH_RATE_IF_NOT_FOUND: int = 5 * _MINUTE
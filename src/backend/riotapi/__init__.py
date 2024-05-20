import yaml

from src.log.log import presetDefaultLogging
from src.utils.static import RIOTAPI_LOG_CFG_FILE

with open(RIOTAPI_LOG_CFG_FILE, 'r') as riotapi_env:
    data = yaml.safe_load(riotapi_env)
    presetDefaultLogging(data['LOGGER'])

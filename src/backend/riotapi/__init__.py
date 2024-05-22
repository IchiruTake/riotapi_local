import gc
import toml
import yaml

from src.log.log import presetDefaultLogging
from src.utils.static import RIOTAPI_LOG_CFG_FILE, RIOTAPI_GC_CFG_FILE

# ==================================================================================================
# PROGRAM INITIALIZATION
# 1. Load the logging configuration
with open(RIOTAPI_LOG_CFG_FILE, 'r') as riotapi_env:
    data = yaml.safe_load(riotapi_env)
    presetDefaultLogging(data['LOGGER'])

# 2. Disable the garbage collector
with open(RIOTAPI_GC_CFG_FILE, 'r') as riotapi_gc:
    gc_settings: dict = toml.load(riotapi_gc)["GC"]
    if gc_settings.get("DISABLE_GC", False) is True:
        gc.disable()
    else:
        if gc_settings.get("CLEANUP_AND_FREEZE", True) is True:
            gc.collect(2)
            gc.freeze()

        if gc_settings.get("DEBUG", False) is True:
            gc.set_debug(gc.DEBUG_STATS)

        ALLO = gc_settings["ALLO"]
        GEN_0 = gc_settings["GEN_0"]
        GEN_1 = gc_settings["GEN_1"]
        gc.set_threshold(ALLO, GEN_0, GEN_1)

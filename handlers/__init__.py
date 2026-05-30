from .city import router as city_router
from .profile import router as profile_router
from .start import router as start_router
from .subscription import router as subscription_router
from .weather import router as weather_router

routers = [
    start_router,
    profile_router,
    subscription_router,
    weather_router,
    city_router,
]

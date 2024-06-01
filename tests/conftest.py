from hypothesis import settings

settings.register_profile("ci", deadline=1000)
settings.load_profile("ci")

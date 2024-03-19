import sentry_sdk


def configure_sentry():
    sentry_sdk.init(
        dsn="https://e1ba36f96ce05e8a812d5ac2d4c89334@o439624.ingest.us.sentry.io/4506929072046080",
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        environment='development'
    )

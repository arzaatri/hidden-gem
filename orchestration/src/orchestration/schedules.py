from dagster import DefaultScheduleStatus, JobDefinition, ScheduleDefinition

from config.settings import load_settings


def build_daily_schedule(job: JobDefinition) -> ScheduleDefinition:
    settings = load_settings()
    return ScheduleDefinition(
        job=job,
        cron_schedule=settings.etl.schedule_cron,
        default_status=DefaultScheduleStatus.RUNNING,
    )

from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

scheduler = AsyncIOScheduler()
_bot = None


def init_scheduler(bot) -> None:
    global _bot
    _bot = bot
    if not scheduler.running:
        scheduler.start()


async def _send_reminder(reminder_id: int, user_id: int, text: str) -> None:
    from database.reminders import mark_reminder_sent
    try:
        await _bot.send_message(user_id, f"🔔 <b>Напоминание:</b>\n{text}", parse_mode="HTML")
    finally:
        await mark_reminder_sent(reminder_id)


async def schedule_reminder(reminder_id: int, user_id: int, text: str, remind_at: datetime) -> None:
    scheduler.add_job(
        _send_reminder,
        trigger=DateTrigger(run_date=remind_at),
        args=[reminder_id, user_id, text],
        id=f"reminder_{reminder_id}",
        replace_existing=True,
    )


def cancel_reminder(reminder_id: int) -> None:
    job_id = f"reminder_{reminder_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


async def restore_reminders(bot) -> None:
    from database.reminders import get_all_pending_reminders
    init_scheduler(bot)
    reminders = await get_all_pending_reminders()
    now = datetime.now()
    for r in reminders:
        remind_at = datetime.fromisoformat(r["remind_at"])
        if remind_at > now:
            await schedule_reminder(r["id"], r["user_id"], r["text"], remind_at)
        else:
            from database.reminders import mark_reminder_sent
            await mark_reminder_sent(r["id"])

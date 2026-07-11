import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import NotificationRepository
from app.models import NotificationStatusLog

@pytest.mark.asyncio
async def test_notification_delivery_state_transitions(db: AsyncSession) -> None:
    repo = NotificationRepository(db)

    # 1. Create a parent notification record
    notification = await repo.create_notification(
        user_id="user_sm_test",
        template_id=None,
        template_variables={"user": "Alice"},
        priority="NORMAL"
    )
    await db.commit()  # Flush/commit to bind to DB

    # 2. Create initial delivery (starts in PENDING)
    delivery = await repo.create_delivery(
        notification_id=notification.id,
        channel="EMAIL",
        status="PENDING"
    )
    await db.commit()
    assert delivery.status == "PENDING"

    # Verify initial transition log (NONE -> PENDING)
    stmt = select(NotificationStatusLog).where(NotificationStatusLog.delivery_id == delivery.id).order_by(NotificationStatusLog.timestamp.asc())
    logs = (await db.execute(stmt)).scalars().all()
    assert len(logs) == 1
    assert logs[0].from_status == "NONE"
    assert logs[0].to_status == "PENDING"

    # 3. Transition: PENDING -> SENT
    updated = await repo.update_delivery_status(delivery.id, "SENT")
    assert updated is not None
    assert updated.status == "SENT"

    # Verify log entry (PENDING -> SENT)
    logs = (await db.execute(stmt)).scalars().all()
    assert len(logs) == 2
    assert logs[1].from_status == "PENDING"
    assert logs[1].to_status == "SENT"

    # 4. Transition: SENT -> DELIVERED
    updated = await repo.update_delivery_status(delivery.id, "DELIVERED")
    assert updated is not None
    assert updated.status == "DELIVERED"

    # Verify log entry (SENT -> DELIVERED)
    logs = (await db.execute(stmt)).scalars().all()
    assert len(logs) == 3
    assert logs[2].from_status == "SENT"
    assert logs[2].to_status == "DELIVERED"

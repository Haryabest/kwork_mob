"""Webhooks: ЮKassa (верификация через GET /payments/{id})."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import Company, Order, Transaction, User
from app.services.events import publish_order_status
from app.services.queue import queue_service
from app.services.task_lifecycle import try_queue_awaiting_orders
from app.services.yookassa import yookassa_service

router = APIRouter()


def _payment_channel_label(meta: dict, payment: dict) -> str:
    method = str(meta.get("payment_method") or "")
    pm = payment.get("payment_method") or {}
    pm_type = str(pm.get("type") or "")
    if method == "sbp_qr" or pm_type == "sbp":
        return "СБП"
    return "ЮKassa"


@router.post("/yookassa")
async def yookassa_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Обработка платежей/возвратов ЮKassa: IP + GET object (§8.4.1)."""
    from app.services import yookassa_webhook_alerts as yk_wh
    from app.services import yookassa_webhook_auth as yk_auth

    yookassa_service.require_configured()
    client_ip = yk_auth.assert_webhook_ip(request)
    body = await request.json()
    parsed = yookassa_service.parse_webhook(body)
    event = parsed.get("event")
    payment_id = parsed.get("payment_id")
    meta_early = parsed.get("metadata") or {}
    order_hint = meta_early.get("order_id")

    # --- refund.succeeded (§8) ---
    if event == "refund.succeeded":
        refund_id = parsed.get("refund_id")
        if not refund_id:
            return {"ok": True, "ignored": True, "reason": "no_refund_id"}
        try:
            refund = await yookassa_service.get_refund(refund_id)
            if refund.get("status") != "succeeded":
                return {"ok": True, "ignored": True, "status": refund.get("status")}
            pay_id = str(refund.get("payment_id") or payment_id or "")
            amount = int(float((refund.get("amount") or {}).get("value") or parsed.get("amount") or 0))
            existing = await db.scalar(
                select(Transaction).where(Transaction.external_id == f"refund:{refund_id}")
            )
            if existing:
                await yk_wh.record_webhook_success(order_hint or pay_id)
                return {"ok": True, "idempotent": True, "refund_id": refund_id}

            order = None
            if pay_id:
                order = await db.scalar(select(Order).where(Order.yookassa_payment_id == pay_id))
            user_id = None
            company_id = None
            if order:
                user_id = order.user_id
                company_id = order.company_id
                order_hint = order.id
            db.add(
                Transaction(
                    user_id=user_id,
                    company_id=company_id,
                    amount=amount,
                    tx_type="refund",
                    description=f"ЮKassa refund.succeeded refund_id={refund_id} payment={pay_id}"
                    + (f" order=#{order.id}" if order else ""),
                    external_id=f"refund:{refund_id}",
                )
            )
            await db.commit()
            if user_id:
                try:
                    from app.services import push as push_svc

                    await push_svc.send_to_user(
                        db,
                        user_id,
                        "Возврат средств",
                        f"Возврат {amount} ₽ через ЮKassa подтверждён.",
                        data={"refund_id": refund_id, "payment_id": pay_id},
                        email_fallback=True,
                    )
                except Exception:  # noqa: BLE001
                    pass
            await yk_wh.record_webhook_success(order_hint or pay_id or refund_id)
            return {
                "ok": True,
                "refund_id": refund_id,
                "payment_id": pay_id,
                "amount": amount,
                "order_id": order.id if order else None,
                "ip": client_ip,
            }
        except HTTPException as exc:
            await yk_wh.record_webhook_failure(
                order_id=order_hint,
                payment_id=payment_id or refund_id,
                detail=str(exc.detail),
            )
            raise
        except Exception as exc:  # noqa: BLE001
            await yk_wh.record_webhook_failure(
                order_id=order_hint,
                payment_id=payment_id or refund_id,
                detail=str(exc)[:400],
            )
            raise

    if not payment_id:
        return {"ok": True, "ignored": True}

    try:
        if event not in ("payment.succeeded", "payment.waiting_for_capture") and parsed.get(
            "status"
        ) != "succeeded":
            return {"ok": True, "ignored": True, "event": event}

        payment = await yookassa_service.get_payment(payment_id)
        if payment.get("status") != "succeeded":
            return {"ok": True, "ignored": True, "status": payment.get("status"), "ip": client_ip}
        yk_auth.assert_payment_authentic(payment=payment, payment_id=payment_id)

        existing = await db.scalar(select(Transaction).where(Transaction.external_id == payment_id))
        if existing:
            await yk_wh.record_webhook_success(order_hint or existing.external_id)
            return {"ok": True, "idempotent": True}

        meta = payment.get("metadata") or parsed.get("metadata") or {}
        purpose = str(meta.get("purpose") or "topup")
        user_id = int(meta.get("user_id") or 0)
        amount = int(float((payment.get("amount") or {}).get("value") or parsed.get("amount") or 0))
        if not user_id or amount <= 0:
            raise HTTPException(400, "bad metadata")

        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(400, "user not found")

        channel = _payment_channel_label(meta, payment)
        order_id_for_streak = meta.get("order_id")

        if purpose == "company_topup":
            company_id = int(meta.get("company_id") or 0)
            company = await db.get(Company, company_id) if company_id else None
            if not company or company.owner_id != user.id:
                raise HTTPException(400, "company not found")
            company.balance += amount
            db.add(
                Transaction(
                    user_id=user.id,
                    company_id=company.id,
                    amount=amount,
                    tx_type="topup",
                    description=f"Пополнение баланса компании через {channel}",
                    external_id=payment_id,
                )
            )
            await db.commit()
            await yk_wh.record_webhook_success(company_id)
            return {"ok": True, "company_id": company.id, "credited": amount}

        if purpose == "order":
            order_id = int(meta.get("order_id") or 0)
            order_id_for_streak = order_id
            order = await db.get(Order, order_id) if order_id else None
            if not order or order.user_id != user.id:
                raise HTTPException(400, "order not found")
            if order.status not in ("awaiting_payment", "pending", "paid"):
                await yk_wh.record_webhook_success(order_id)
                return {"ok": True, "ignored": True, "order_status": order.status}

            from app.services.nsfw import nsfw_service

            db.add(
                Transaction(
                    user_id=user.id,
                    company_id=order.company_id,
                    amount=amount,
                    tx_type="topup",
                    description=f"Оплата заказа #{order.id} через {channel}",
                    external_id=payment_id,
                )
            )
            user.balance += amount

            from app.services import photo_encryption as photo_enc

            enc_key = await photo_enc.get_key(order.task_uuid)
            nsfw = await nsfw_service.check_task_photos(
                order.task_uuid, decryption_key=enc_key
            )
            if nsfw.get("is_nsfw"):
                await nsfw_service.block_order(
                    db, order=order, user=user, result=nsfw, refund=True, charged=False
                )
                await db.commit()
                await yk_wh.record_webhook_success(order_id)
                return {"ok": True, "order_id": order.id, "blocked_nsfw": True}

            db.add(
                Transaction(
                    user_id=user.id,
                    company_id=order.company_id,
                    amount=-order.amount,
                    tx_type="charge",
                    description=f"Заказ #{order.id}",
                )
            )
            user.balance -= order.amount
            order.status = "queued"
            order.yookassa_payment_id = payment_id
            payload = {
                "category": order.category,
                "tier": order.tier,
                "user_id": user.id,
                "order_id": order.id,
                "company_id": order.company_id,
                "photos_bucket": settings.MINIO_BUCKET_PHOTOS,
                "photos_prefix": f"photos/{order.task_uuid}/",
                "models_bucket": settings.MINIO_BUCKET_MODELS,
                "zip_sha256": order.zip_sha256,
                "device_model": order.device_model or "unknown",
                "os_version": order.os_version or "unknown",
            }
            if enc_key:
                payload["photo_encryption_key"] = enc_key
                payload["photo_encryption_alg"] = photo_enc.ALGORITHM
            await queue_service.enqueue(
                db,
                task_id=order.task_uuid,
                order_id=order.id,
                company_id=order.company_id,
                payload=payload,
                priority="high" if order.tier == "large" else "normal",
            )
            await db.commit()
            await publish_order_status(
                user_id=user.id,
                order_id=order.id,
                task_id=order.task_uuid,
                status="queued",
            )
            await yk_wh.record_webhook_success(order_id)
            return {"ok": True, "order_id": order.id, "queued": True}

        # topup личного баланса
        user.balance += amount
        db.add(
            Transaction(
                user_id=user.id,
                amount=amount,
                tx_type="topup",
                description=f"Пополнение через {channel}",
                external_id=payment_id,
            )
        )
        await db.flush()
        queued = await try_queue_awaiting_orders(db, user.id)
        await db.commit()
        await yk_wh.record_webhook_success(user_id)
        return {"ok": True, "credited": amount, "queued_orders": queued}

    except HTTPException as exc:
        await yk_wh.record_webhook_failure(
            order_id=order_hint,
            payment_id=payment_id,
            detail=str(exc.detail),
        )
        raise
    except Exception as exc:  # noqa: BLE001
        await yk_wh.record_webhook_failure(
            order_id=order_hint,
            payment_id=payment_id,
            detail=str(exc)[:400],
        )
        raise

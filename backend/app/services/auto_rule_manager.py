import logging
from sqlalchemy import select

logger = logging.getLogger("ainis.rule_engine")


async def evaluate_rules(
    session_factory,
    congestion_score: float,
    anomaly_score: float,
):
    try:
        from app.models.routing_rule import RoutingRule

        async with session_factory() as session:

            result = await session.execute(select(RoutingRule))

            rules = result.scalars().all()

            changed = False

            for rule in rules:

                previous = rule.active

                if congestion_score > 0.70:
                    if rule.bandwidth_limit_kbps is not None:
                        rule.active = True

                if anomaly_score > 0.80:
                    if rule.dst_port in [443, 22]:
                        rule.active = True
                        rule.priority = 1

                if congestion_score < 0.30 and anomaly_score < 0.30:
                    pass

                if previous != rule.active:
                    changed = True

            if changed:
                await session.commit()
                logger.info("[rule_engine] rules updated")

            logger.info(
                f"[rule_engine] evaluated "
                f"congestion={congestion_score:.3f} "
                f"anomaly={anomaly_score:.3f}"
            )

    except Exception as e:
        logger.error(f"[rule_engine] failed: {e}")

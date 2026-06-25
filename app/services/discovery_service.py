import logging
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.chat_message import ChatMessage
from app.models.deal import Deal
from app.models.task import Task
from app.config import settings

logger = logging.getLogger("discovery")


class DiscoveryService:
    def __init__(self):
        self.last_report_date = None

    async def analyze_chat_patterns(self, db: AsyncSession, brokerage_id: int) -> dict[str, Any]:
        """Analyze broker chat messages for patterns and feature gaps."""
        cutoff = datetime.utcnow() - timedelta(days=7)
        result = await db.execute(
            select(ChatMessage).where(
                ChatMessage.brokerage_id == brokerage_id,
                ChatMessage.role == "user",
                ChatMessage.created_at >= cutoff,
            ).order_by(ChatMessage.created_at.desc()).limit(100)
        )
        messages = result.scalars().all()

        if not messages:
            return {"status": "no_data", "period": "7 days", "message_count": 0}

        # Simple keyword analysis
        keywords = {
            "excel": 0, "report": 0, "search": 0, "find": 0,
            "commission": 0, "calculate": 0, "remind": 0, "call": 0,
            "convert": 0, "dollar": 0, "price": 0, "area": 0,
            "إكسل": 0, "تقرير": 0, "بحث": 0, "عمولة": 0,
            "حساب": 0, "تذكير": 0, "اتصال": 0, "سعر": 0,
            "مساحة": 0, "دولار": 0, "تحويل": 0,
        }

        for msg in messages:
            content = (msg.content or "").lower()
            for kw in keywords:
                if kw in content:
                    keywords[kw] += 1

        top_keywords = sorted(keywords.items(), key=lambda x: -x[1])[:10]
        top_used = [{"keyword": k, "count": v} for k, v in top_keywords if v > 0]

        # Feature gap suggestions
        gaps = []
        if keywords.get("dollar", 0) + keywords.get("دولار", 0) > 3:
            gaps.append("Users frequently mention USD - consider adding auto EGP/USD conversion tool")
        if keywords.get("excel", 0) + keywords.get("إكسل", 0) > 3:
            gaps.append("High demand for Excel exports - enhance report generation")
        if keywords.get("commission", 0) + keywords.get("عمولة", 0) > 5:
            gaps.append("Commission calculations are common - add quick commission calculator to dashboard")
        if keywords.get("remind", 0) + keywords.get("call", 0) + keywords.get("اتصال", 0) + keywords.get("تذكير", 0) > 5:
            gaps.append("Reminder/call requests frequent - consider auto-reminder from chat")

        return {
            "status": "success",
            "period": "7 days",
            "message_count": len(messages),
            "top_keywords": top_used,
            "feature_gaps": gaps,
            "analysis_date": datetime.utcnow().isoformat(),
        }

    async def generate_weekly_report(self, db: AsyncSession, brokerage_id: int) -> str:
        """Generate a weekly summary report for the admin."""
        data = await self.analyze_chat_patterns(db, brokerage_id)
        self.last_report_date = datetime.utcnow()

        report_parts = [f"=== Discovery Weekly Report ==="]
        report_parts.append(f"Date: {data.get('analysis_date', 'N/A')}")
        report_parts.append(f"Period: {data.get('period', 'N/A')}")
        report_parts.append(f"Messages analyzed: {data.get('message_count', 0)}")

        if data.get("top_keywords"):
            report_parts.append("\nTop keywords:")
            for kw in data["top_keywords"]:
                report_parts.append(f"  - {kw['keyword']}: {kw['count']} times")

        if data.get("feature_gaps"):
            report_parts.append("\nSuggested improvements:")
            for gap in data["feature_gaps"]:
                report_parts.append(f"  ! {gap}")
        else:
            report_parts.append("\nNo feature gaps detected.")

        report = "\n".join(report_parts)
        logger.info(f"Discovery weekly report generated: {len(data.get('feature_gaps', []))} gaps found")
        return report


discovery_service = DiscoveryService()

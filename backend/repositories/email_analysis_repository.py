from typing import Optional

from services.oracle_db_service import get_connection


class EmailAnalysisRepository:
    """Database operations for email AI analysis."""

    def create_analysis(
        self,
        analysis_id: str,
        email_id: str,
        email_type: Optional[str],
        priority: Optional[str],
        confidence: Optional[float],
        extracted_data: Optional[str],
        recommended_action: Optional[str],
        reasoning_summary: Optional[str],
    ) -> None:
        """Store AI analysis for an email."""

        connection = get_connection()
        cursor = connection.cursor()

        try:
            sql = """
                INSERT INTO EMAIL_ANALYSIS (
                    ANALYSIS_ID,
                    EMAIL_ID,
                    EMAIL_TYPE,
                    PRIORITY,
                    CONFIDENCE,
                    EXTRACTED_DATA,
                    RECOMMENDED_ACTION,
                    REASONING_SUMMARY
                )
                VALUES (
                    :analysis_id,
                    :email_id,
                    :email_type,
                    :priority,
                    :confidence,
                    :extracted_data,
                    :recommended_action,
                    :reasoning_summary
                )
            """

            cursor.execute(
                sql,
                {
                    "analysis_id": analysis_id,
                    "email_id": email_id,
                    "email_type": email_type,
                    "priority": priority,
                    "confidence": confidence,
                    "extracted_data": extracted_data,
                    "recommended_action": recommended_action,
                    "reasoning_summary": reasoning_summary,
                },
            )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            cursor.close()
            connection.close()

    def get_analysis(
        self,
        email_id: str,
    ) -> Optional[dict]:
        """Retrieve the latest analysis for an email."""

        connection = get_connection()
        cursor = connection.cursor()

        try:
            sql = """
                SELECT
                    ANALYSIS_ID,
                    EMAIL_ID,
                    EMAIL_TYPE,
                    PRIORITY,
                    CONFIDENCE,
                    EXTRACTED_DATA,
                    RECOMMENDED_ACTION,
                    REASONING_SUMMARY,
                    ANALYZED_DATE
                FROM EMAIL_ANALYSIS
                WHERE EMAIL_ID = :email_id
                ORDER BY ANALYZED_DATE DESC
                FETCH FIRST 1 ROW ONLY
            """

            cursor.execute(
                sql,
                {"email_id": email_id},
            )

            row = cursor.fetchone()

            if not row:
                return None

            return {
                "analysis_id": row[0],
                "email_id": row[1],
                "email_type": row[2],
                "priority": row[3],
                "confidence": row[4],
                "extracted_data": row[5],
                "recommended_action": row[6],
                "reasoning_summary": row[7],
                "analyzed_date": row[8],
            }

        finally:
            cursor.close()
            connection.close()
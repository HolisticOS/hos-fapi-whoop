"""
Raw WHOOP Data Storage Service
Simple JSON storage approach for MVP
"""
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import structlog
from app.config.database import get_supabase_client

logger = structlog.get_logger(__name__)

class WhoopRawDataStorage:
    """Service for storing raw WHOOP API data as JSON in Supabase"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.table_name = 'whoop_raw_data'
    
    async def store_whoop_data(
        self,
        user_id: str,
        data_type: str,
        records: List[Dict[str, Any]],
        next_token: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        whoop_user_id: Optional[int] = None
    ) -> bool:
        """
        Store raw WHOOP data in Supabase
        
        Args:
            user_id: Internal user ID (e.g., 'user002')
            data_type: Type of data ('sleep', 'recovery', 'workout', 'cycle', 'profile')
            records: Raw records from WHOOP API
            next_token: Pagination token if available
            api_endpoint: Source API endpoint for debugging
            whoop_user_id: WHOOP's numeric user ID from API
            
        Returns:
            bool: Success status
        """
        try:
            # Extract WHOOP user ID from first record if not provided
            if not whoop_user_id and records and len(records) > 0:
                whoop_user_id = records[0].get('user_id')
            
            # Prepare data for storage
            storage_data = {
                'user_id': user_id,
                'whoop_user_id': whoop_user_id,
                'data_type': data_type,
                'records': records,
                'record_count': len(records),
                'next_token': next_token,
                'api_endpoint': api_endpoint,
                'fetched_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Store in Supabase
            result = self.supabase.table(self.table_name).insert(storage_data).execute()
            
            if result.data:
                logger.info(
                    "✅ Stored WHOOP data",
                    user_id=user_id,
                    data_type=data_type,
                    record_count=len(records),
                    storage_id=result.data[0]['id']
                )
                return True
            else:
                logger.error(
                    "❌ Failed to store WHOOP data - no result",
                    user_id=user_id,
                    data_type=data_type
                )
                return False
                
        except Exception as e:
            logger.error(
                "❌ Error storing WHOOP data",
                user_id=user_id,
                data_type=data_type,
                error=str(e)
            )
            return False
    
    async def get_latest_data(
        self,
        user_id: str,
        data_type: str,
        limit: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent data for a user and type
        
        Args:
            user_id: Internal user ID
            data_type: Type of data to retrieve
            limit: Number of results to return
            
        Returns:
            Latest stored data or None
        """
        try:
            result = self.supabase.table(self.table_name)\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('data_type', data_type)\
                .order('fetched_at', desc=True)\
                .limit(limit)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0] if limit == 1 else result.data
            return None
            
        except Exception as e:
            logger.error(
                "❌ Error retrieving WHOOP data",
                user_id=user_id,
                data_type=data_type,
                error=str(e)
            )
            return None
    
    async def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get summary of stored data for a user
        
        Args:
            user_id: Internal user ID
            
        Returns:
            Summary dict with counts and last update times
        """
        try:
            result = self.supabase.table(self.table_name)\
                .select('data_type, record_count, fetched_at')\
                .eq('user_id', user_id)\
                .order('fetched_at', desc=True)\
                .execute()
            
            summary = {}
            for row in result.data:
                data_type = row['data_type']
                if data_type not in summary:
                    summary[data_type] = {
                        'total_records': 0,
                        'last_updated': row['fetched_at'],
                        'fetch_count': 0
                    }
                
                summary[data_type]['total_records'] += row['record_count']
                summary[data_type]['fetch_count'] += 1
                
                # Keep the most recent update time
                if row['fetched_at'] > summary[data_type]['last_updated']:
                    summary[data_type]['last_updated'] = row['fetched_at']
            
            return summary
            
        except Exception as e:
            logger.error(
                "❌ Error getting user summary",
                user_id=user_id,
                error=str(e)
            )
            return {}
    
    async def cleanup_old_data(
        self,
        user_id: str,
        data_type: str,
        keep_latest_n: int = 5
    ) -> bool:
        """
        Clean up old data keeping only the latest N entries
        
        Args:
            user_id: Internal user ID
            data_type: Type of data to clean up
            keep_latest_n: Number of latest entries to keep
            
        Returns:
            Success status
        """
        try:
            # Get IDs of records to keep
            keep_result = self.supabase.table(self.table_name)\
                .select('id')\
                .eq('user_id', user_id)\
                .eq('data_type', data_type)\
                .order('fetched_at', desc=True)\
                .limit(keep_latest_n)\
                .execute()
            
            if not keep_result.data:
                return True  # Nothing to clean up
            
            keep_ids = [row['id'] for row in keep_result.data]
            
            # Delete older records
            delete_result = self.supabase.table(self.table_name)\
                .delete()\
                .eq('user_id', user_id)\
                .eq('data_type', data_type)\
                .not_.in_('id', keep_ids)\
                .execute()
            
            deleted_count = len(delete_result.data) if delete_result.data else 0
            
            logger.info(
                "🧹 Cleaned up old WHOOP data",
                user_id=user_id,
                data_type=data_type,
                deleted_count=deleted_count,
                kept_latest=keep_latest_n
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "❌ Error cleaning up data",
                user_id=user_id,
                data_type=data_type,
                error=str(e)
            )
            return False
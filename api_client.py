import requests
import os
from typing import Dict, List, Optional
import time

class KalshiAPIClient:
    """
    Kalshi API client with authentication and rate limiting
    """
    
    def __init__(self):
        self.base_url = "https://api.elections.kalshi.com/trade-api/v2"
        self.email = os.environ.get('KALSHI_EMAIL')
        self.password = os.environ.get('KALSHI_API_KEY')
        self.token = None
        self.token_expiry = 0
        
    def _get_auth_token(self) -> str:
        """Get or refresh authentication token"""
        current_time = time.time()
        
        # Reuse token if still valid (tokens last ~24 hours)
        if self.token and current_time < self.token_expiry:
            return self.token

            # Get new token
        response = requests.post(
            f"{self.base_url}/login",
            json={
                "email": self.email,
                "password": self.password
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Kalshi auth failed: {response.text}")
            
        data = response.json()
        self.token = data['token']
        # Set expiry to 23 hours from now (tokens last 24h)
        self.token_expiry = current_time + (23 * 60 * 60)
        
        return self.token
    
    def get_markets(self, limit: int = 100, cursor: Optional[str] = None) -> Dict:
        """
        Fetch markets from Kalshi
        
        Args:
            limit: Number of markets to fetch (max 1000)
            cursor: Pagination cursor for fetching more results
            
        Returns:
            Dict with 'markets' list and optional 'cursor' for pagination
        """
        token = self._get_auth_token()

        params = {
            'limit': limit,
            'status': 'open'
        }
        
        if cursor:
            params['cursor'] = cursor
            
        response = requests.get(
            f"{self.base_url}/markets",
            headers={'Authorization': f'Bearer {token}'},
            params=params
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch markets: {response.text}")
            
        return response.json()
    
    def get_market_orderbook(self, ticker: str) -> Dict:
        """
        Get orderbook for a specific market
        
        Args:
            ticker: Market ticker symbol
            
        Returns:
            Dict with bid/ask prices and depth
        """
        token = self._get_auth_token()

        response = requests.get(
            f"{self.base_url}/markets/{ticker}/orderbook",
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch orderbook: {response.text}")
            
        return response.json()
    
    def get_market_history(self, ticker: str, limit: int = 100) -> Dict:
        """
        Get trade history for a market
        
        Args:
            ticker: Market ticker symbol
            limit: Number of historical trades to fetch
            
        Returns:
            Dict with trade history
        """
        token = self._get_auth_token()
        
        response = requests.get(
            f"{self.base_url}/markets/{ticker}/history",
            headers={'Authorization': f'Bearer {token}'},
            params={'limit': limit}
        )
        
        if response.status_code != 200:
            return {'trades': []}
            
        return response.json()

        _kalshi_client = None

def get_kalshi_client() -> KalshiAPIClient:
    """Get or create Kalshi API client singleton"""
    global _kalshi_client
    if _kalshi_client is None:
        _kalshi_client = KalshiAPIClient()
    return _kalshi_client

from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import requests
import base64
import datetime
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding

app = Flask(__name__)

CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

class KalshiClient:
    def __init__(self):
        self.base_url = "https://api.elections.kalshi.com"
        self.api_key = os.environ.get('KALSHI_API_KEY')
        
        # Handle private key with proper newline conversion
        private_key_raw = os.environ.get('KALSHI_PRIVATE_KEY', '')
        # Try multiple replacement strategies
        if '\\n' in private_key_raw:
            private_key_raw = private_key_raw.replace('\\n', '\n')
        
        # Ensure proper PEM formatting
        if not private_key_raw.startswith('-----BEGIN'):
            raise ValueError("Invalid private key format")
        
        try:
            self.private_key = serialization.load_pem_private_key(
                private_key_raw.encode('utf-8'),
                password=None,
                backend=default_backend()
            )
        except Exception as e:
            print(f"Private key error: {e}")
            print(f"Key starts with: {private_key_raw[:50]}")
            raise
    
    def create_signature(self, timestamp, method, path):
        path_without_query = path.split('?')[0]
        message = f"{timestamp}{method}{path_without_query}".encode('utf-8')
        signature = self.private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')
    
    def make_request(self, method, path, params=None):
        timestamp = str(int(datetime.datetime.now().timestamp() * 1000))
        signature = self.create_signature(timestamp, method, path)
        headers = {
            'KALSHI-ACCESS-KEY': self.api_key,
            'KALSHI-ACCESS-SIGNATURE': signature,
            'KALSHI-ACCESS-TIMESTAMP': timestamp
        }
        url = self.base_url + path
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=params)
        else:
            raise ValueError(f"Unsupported method: {method}")
        if response.status_code != 200:
            raise Exception(f"Kalshi API error: {response.status_code} {response.text}")
        return response.json()
    
    def get_series(self, limit=200):
        """Get series (parent market categories) - these are the real markets!"""
        return self.make_request('GET', '/trade-api/v2/series', {'limit': limit})
    
    def get_markets_for_series(self, series_ticker):
        """Get specific markets within a series"""
        return self.make_request('GET', '/trade-api/v2/markets', {
            'series_ticker': series_ticker,
            'status': 'open'
        })

client = KalshiClient()

def calculate_inefficiency_score(market_data):
    """
    Score market inefficiency based on spread, liquidity, and activity.
    """
    yes_bid = market_data.get('yes_bid', 0)
    yes_ask = market_data.get('yes_ask', 100)
    open_interest = market_data.get('open_interest', 0)
    volume_24h = market_data.get('volume_24h', 0)
    
    # FILTER OUT DEAD/ILLIQUID MARKETS
    # Require BOTH meaningful liquidity AND recent activity
    if open_interest < 50:
        return None  # Too thin
    if volume_24h < 5:
        return None  # No recent trading
    
    # Skip markets with no price discovery
    if yes_bid == 0 and yes_ask == 100:
        return None
    
    # Calculate spread metrics
    mid_price = (yes_bid + yes_ask) / 2
    if mid_price == 0:
        return None
    
    spread = yes_ask - yes_bid
    spread_pct = spread / mid_price
    
    # Use Kalshi's actual metrics
    open_interest = market_data.get('open_interest', 0)
    volume_24h = market_data.get('volume_24h', 0)
    last_price = market_data.get('last_price', 0)
    
    # Liquidity-Volume Spread (LVS) Score
    lvs_score = (spread_pct * 100) * (1000 / max(open_interest, 1))
    
    # Market Depth Ratio (MDR) Score  
    mdr_score = spread_pct * 100 * (500 / max(volume_24h + 1, 1))
    
    # Combined inefficiency score
    inefficiency_score = (lvs_score * 0.6) + (mdr_score * 0.4)
    
    # Opportunity criteria - more relaxed to find actual markets
    is_opportunity = (
        spread_pct > 0.02 and 
        inefficiency_score > 20
    )
    
    # Analysis categories
    if spread_pct > 0.10:
        analysis = 'Very wide spread (>10%) - high inefficiency'
    elif spread_pct > 0.05:
        analysis = 'Wide spread (5-10%) - moderate inefficiency'
    elif spread_pct > 0.02:
        analysis = 'Moderate spread (2-5%) - potential opportunity'
    else:
        analysis = 'Tight spread (<2%) - efficient market'
    
    return {
        'ticker': market_data.get('ticker', ''),
        'title': market_data.get('title', ''),
        'series_ticker': market_data.get('series_ticker', ''),
        'lvs_score': round(lvs_score, 2),
        'mdr_score': round(mdr_score, 2),
        'inefficiency_score': round(inefficiency_score, 2),
        'is_opportunity': is_opportunity,
        'spread_pct': round(spread_pct * 100, 2),
        'mid_price': round(mid_price, 2),
        'yes_bid': yes_bid,
        'yes_ask': yes_ask,
        'open_interest': open_interest,
        'volume_24h': volume_24h,
        'last_price': last_price,
        'analysis': analysis,
        'category': market_data.get('category', 'Other')
    }

@app.route('/')
def health_check():
    return jsonify({'status': 'healthy', 'service': 'Kalshi Radar API', 'version': '3.0.0'})

@app.route('/api/health')
def api_health():
    return jsonify({'status': 'ok', 'kalshi_api': 'connected', 'scoring_engine': 'active'})

@app.route('/api/series', methods=['GET'])
def get_series():
    """Get all available series (market categories)"""
    try:
        limit = int(request.args.get('limit', 200))
        data = client.get_series(limit=limit)
        series_list = []
        for series in data.get('series', []):
            series_list.append({
                'ticker': series.get('ticker', ''),
                'title': series.get('title', ''),
                'category': series.get('category', 'Other'),
                'frequency': series.get('frequency', '')
            })
        return jsonify({'series': series_list, 'count': len(series_list)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/markets', methods=['GET'])
def get_markets():
    """Get markets from series (non-parlay markets)"""
    try:
        limit = int(request.args.get('limit', 50))
        category_filter = request.args.get('category', None)
        
        # Get series first
        series_data = client.get_series(limit=200)
        
        # Filter by category if specified
        series_list = series_data.get('series', [])
        if category_filter:
            series_list = [s for s in series_list if s.get('category', '').lower() == category_filter.lower()]
        
        # Get markets from each series (limit to first N series to avoid timeout)
        all_markets = []
        series_checked = 0
        max_series = 20  # Check first 20 series to avoid timeout
        
        for series in series_list[:max_series]:
            series_checked += 1
            try:
                markets = client.get_markets_for_series(series['ticker'])
                for market in markets.get('markets', [])[:5]:  # Max 5 markets per series
                    all_markets.append({
                        'ticker': market.get('ticker', ''),
                        'title': market.get('title', ''),
                        'series_ticker': series['ticker'],
                        'category': series.get('category', 'Other'),
                        'yes_bid': market.get('yes_bid', 0),
                        'yes_ask': market.get('yes_ask', 100),
                        'open_interest': market.get('open_interest', 0),
                        'volume_24h': market.get('volume_24h', 0),
                        'last_price': market.get('last_price', 0)
                    })
                    if len(all_markets) >= limit:
                        break
            except:
                continue
            if len(all_markets) >= limit:
                break
        
        return jsonify({
            'markets': all_markets[:limit],
            'count': len(all_markets[:limit]),
            'series_checked': series_checked
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scores', methods=['GET'])
def get_scores():
    try:
        limit = int(request.args.get('limit', 50))
        category_filter = request.args.get('category', None)
        
        # Get series first
        series_data = client.get_series(limit=200)
        series_list = series_data.get('series', [])
        
        if category_filter:
            series_list = [s for s in series_list if s.get('category', '').lower() == category_filter.lower()]
        
        scored_markets = []
        series_checked = 0
        max_series = 30
        
        for series in series_list[:max_series]:
            series_checked += 1
            try:
                markets = client.get_markets_for_series(series['ticker'])
                for market in markets.get('markets', [])[:5]:
                    market['series_ticker'] = series['ticker']
                    market['category'] = series.get('category', 'Other')
                    score = calculate_inefficiency_score(market)
                    if score:
                        scored_markets.append(score)
                        if len(scored_markets) >= limit * 2:  # Get more than needed, then sort
                            break
            except:
                continue
            if len(scored_markets) >= limit * 2:
                break
        
        scored_markets.sort(key=lambda x: x['inefficiency_score'], reverse=True)
        opportunities = [m for m in scored_markets if m['is_opportunity']]
        
        return jsonify({
            'scores': scored_markets[:limit],
            'opportunities_found': len(opportunities),
            'total_scored': len(scored_markets),
            'series_checked': series_checked
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/opportunities', methods=['GET'])
def get_opportunities():
    try:
        limit = int(request.args.get('limit', 50))
        category_filter = request.args.get('category', None)
        
        # Get series first
        series_data = client.get_series(limit=200)
        series_list = series_data.get('series', [])
        
        if category_filter:
            series_list = [s for s in series_list if s.get('category', '').lower() == category_filter.lower()]
        
        opportunities = []
        series_checked = 0
        max_series = 50
        
        for series in series_list[:max_series]:
            series_checked += 1
            try:
                markets = client.get_markets_for_series(series['ticker'])
                for market in markets.get('markets', [])[:10]:
                    market['series_ticker'] = series['ticker']
                    market['category'] = series.get('category', 'Other')
                    score = calculate_inefficiency_score(market)
                    if score and score['is_opportunity']:
                        opportunities.append(score)
                        if len(opportunities) >= limit:
                            break
            except:
                continue
            if len(opportunities) >= limit:
                break
        
        return jsonify({
            'opportunities': opportunities,
            'count': len(opportunities),
            'series_checked': series_checked
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
